"""
Database manager cho Login Sessions + Chat History.

Quản lý phiên đăng nhập và lịch sử chat qua SQLite:
- Login Sessions: One-time use, TTL 10 phút, auto-cleanup
- Chat History: Lưu lịch sử chat theo tài khoản user (email)

Tham chiếu:
    - docs/DOCS-main/skill_sql_compatibility.md
    - docs/DOCS-main/skill_security_authentication.md
"""

import hashlib
import json
import sqlite3
import os
from datetime import datetime, timedelta
from pathlib import Path

from app.logger import get_logger

logger = get_logger(__name__)


# Database file path
DB_DIR = Path(__file__).parent.parent / "data"
DB_PATH = DB_DIR / "login_sessions.db"

# Session TTL (10 phút)
SESSION_TTL_MINUTES = 10


def get_gravatar_url(email: str) -> str:
    """
    Sinh URL Gravatar từ email (Lớp 1 trong Avatar Fallback 3 lớp).
    Nếu Gravatar không có ảnh, trả về identicon tự sinh.

    Args:
        email: Email của user.

    Returns:
        URL ảnh Gravatar hoặc identicon.

    Tham chiếu: docs/DOCS-main/skill_security_authentication.md Mục 2.
    """
    email_hash = hashlib.md5(email.strip().lower().encode("utf-8")).hexdigest()
    return f"https://www.gravatar.com/avatar/{email_hash}?d=identicon"


class UserDB:
    """Quản lý SQLite database cho login sessions và chat history."""

    def __init__(self, db_path: str = None):
        """
        Khởi tạo kết nối đến SQLite database.

        Args:
            db_path: Đường dẫn đến file database. Mặc định: chatbot/data/login_sessions.db
        """
        self.db_path = db_path or str(DB_PATH)

        # Đảm bảo thư mục tồn tại
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()

        # Tạo bảng nếu chưa có
        self._create_tables()

    def _create_tables(self):
        """Tạo bảng login_sessions, users và chat_messages nếu chưa tồn tại."""
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS login_sessions (
                session_id TEXT PRIMARY KEY,
                token TEXT,
                status TEXT DEFAULT 'pending',
                user_email TEXT,
                user_name TEXT,
                user_picture TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Bảng users — lưu thông tin user đã đăng nhập
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                name TEXT,
                picture TEXT,
                gravatar_url TEXT,
                is_admin INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_email TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('user', 'bot')),
                content TEXT NOT NULL,
                sources TEXT DEFAULT '[]',
                response_time REAL,
                num_docs INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Index cho truy vấn nhanh theo user_email
        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_chat_user_email 
            ON chat_messages(user_email)
        """)

        self.conn.commit()

    # ------------------------------------------------------------------
    # User Management
    # ------------------------------------------------------------------

    def upsert_user(self, email: str, name: str = None, picture: str = None) -> dict:
        """
        Tạo hoặc cập nhật user khi đăng nhập.
        Tự động sinh Gravatar URL nếu user không có picture.

        Args:
            email: Email của user.
            name: Tên hiển thị.
            picture: URL ảnh avatar từ Google.

        Returns:
            Dict chứa thông tin user.
        """
        gravatar = get_gravatar_url(email)
        # Nếu không có picture từ Google, dùng Gravatar
        final_picture = picture or gravatar

        self.cursor.execute("""
            INSERT INTO users (email, name, picture, gravatar_url, last_login)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(email) DO UPDATE SET
                name = excluded.name,
                picture = excluded.picture,
                gravatar_url = excluded.gravatar_url,
                last_login = CURRENT_TIMESTAMP
        """, (email, name, final_picture, gravatar))
        self.conn.commit()

        return self.get_user_by_email(email)

    def get_user_by_email(self, email: str) -> dict | None:
        """
        Lấy thông tin user theo email.

        Args:
            email: Email của user.

        Returns:
            Dict chứa thông tin user hoặc None.
        """
        self.cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        row = self.cursor.fetchone()
        if not row:
            return None
        return {
            "id": row["id"],
            "email": row["email"],
            "name": row["name"],
            "picture": row["picture"],
            "gravatar_url": row["gravatar_url"],
            "is_admin": bool(row["is_admin"]),
            "created_at": row["created_at"],
            "last_login": row["last_login"],
        }

    # ------------------------------------------------------------------
    # Login Sessions
    # ------------------------------------------------------------------

    def create_login_session(self, session_id: str) -> bool:
        """
        Tạo phiên đăng nhập mới với trạng thái 'pending'.

        Args:
            session_id: UUID của phiên đăng nhập.

        Returns:
            True nếu tạo thành công, False nếu session_id đã tồn tại.
        """
        try:
            self.cursor.execute(
                "INSERT INTO login_sessions (session_id, status) VALUES (?, 'pending')",
                (session_id,)
            )
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def get_login_session(self, session_id: str) -> dict | None:
        """
        Lấy thông tin phiên đăng nhập.

        Chỉ trả về session còn hiệu lực (< TTL).
        Nếu session đã completed và có token, XÓA NGAY session (one-time use).

        Args:
            session_id: UUID của phiên đăng nhập.

        Returns:
            Dict chứa thông tin session hoặc None nếu không tìm thấy/hết hạn.
        """
        self.cursor.execute(
            "SELECT * FROM login_sessions WHERE session_id = ?",
            (session_id,)
        )
        row = self.cursor.fetchone()

        if not row:
            return None

        # Kiểm tra TTL
        created_at = datetime.fromisoformat(row["created_at"])
        if datetime.utcnow() - created_at > timedelta(minutes=SESSION_TTL_MINUTES):
            self.delete_login_session(session_id)
            return None

        result = {
            "session_id": row["session_id"],
            "token": row["token"],
            "status": row["status"],
            "user_email": row["user_email"],
            "user_name": row["user_name"],
            "user_picture": row["user_picture"],
            "created_at": row["created_at"],
        }

        # One-time use: Nếu đã completed và có token, xóa session ngay
        if result["status"] == "completed" and result["token"]:
            self.delete_login_session(session_id)

        return result

    def update_login_session(self, session_id: str, token: str,
                              user_email: str = None, user_name: str = None,
                              user_picture: str = None) -> bool:
        """
        Cập nhật token và thông tin user vào session (status -> 'completed').
        Đồng thời upsert user vào bảng users.

        Args:
            session_id: UUID của phiên đăng nhập.
            token: JWT token đã tạo.
            user_email: Email của user từ Google.
            user_name: Tên hiển thị từ Google.
            user_picture: Avatar URL từ Google.

        Returns:
            True nếu cập nhật thành công.
        """
        self.cursor.execute(
            """UPDATE login_sessions 
               SET token = ?, status = 'completed', 
                   user_email = ?, user_name = ?, user_picture = ?
               WHERE session_id = ?""",
            (token, user_email, user_name, user_picture, session_id)
        )
        self.conn.commit()

        # Upsert user vào bảng users
        if user_email:
            self.upsert_user(
                email=user_email,
                name=user_name,
                picture=user_picture
            )

        return self.cursor.rowcount > 0

    def delete_login_session(self, session_id: str) -> bool:
        """
        Xóa phiên đăng nhập.

        Args:
            session_id: UUID của phiên đăng nhập.

        Returns:
            True nếu xóa thành công.
        """
        self.cursor.execute(
            "DELETE FROM login_sessions WHERE session_id = ?",
            (session_id,)
        )
        self.conn.commit()
        return self.cursor.rowcount > 0

    def cleanup_old_sessions(self):
        """
        Xóa tất cả sessions cũ hơn TTL (10 phút).
        Được gọi tự động mỗi khi tạo session mới để giữ DB sạch.
        """
        cutoff = (datetime.utcnow() - timedelta(minutes=SESSION_TTL_MINUTES)).isoformat()
        self.cursor.execute(
            "DELETE FROM login_sessions WHERE created_at < ?",
            (cutoff,)
        )
        deleted = self.cursor.rowcount
        self.conn.commit()
        if deleted > 0:
            logger.info(f"Đã dọn dẹp {deleted} session(s) hết hạn.")

    # ------------------------------------------------------------------
    # Chat History
    # ------------------------------------------------------------------

    def save_chat_message(self, user_email: str, role: str, content: str,
                          sources: list = None, response_time: float = None,
                          num_docs: int = 0) -> int:
        """
        Lưu một tin nhắn chat vào lịch sử.

        Args:
            user_email: Email của user (khóa phân biệt lịch sử).
            role: 'user' hoặc 'bot'.
            content: Nội dung tin nhắn.
            sources: Danh sách tài liệu nguồn (chỉ cho bot).
            response_time: Thời gian phản hồi (chỉ cho bot).
            num_docs: Số tài liệu sử dụng (chỉ cho bot).

        Returns:
            ID của tin nhắn vừa lưu.
        """
        sources_json = json.dumps(sources or [], ensure_ascii=False)

        self.cursor.execute(
            """INSERT INTO chat_messages 
               (user_email, role, content, sources, response_time, num_docs)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (user_email, role, content, sources_json, response_time, num_docs)
        )
        self.conn.commit()
        return self.cursor.lastrowid

    def get_chat_history(self, user_email: str, limit: int = 100,
                         offset: int = 0) -> list[dict]:
        """
        Lấy lịch sử chat của user, sắp xếp từ cũ đến mới.

        Args:
            user_email: Email của user.
            limit: Số tin nhắn tối đa trả về. Mặc định: 100.
            offset: Bỏ qua bao nhiêu tin nhắn đầu. Mặc định: 0.

        Returns:
            Danh sách dict tin nhắn.
        """
        self.cursor.execute(
            """SELECT * FROM chat_messages 
               WHERE user_email = ? 
               ORDER BY created_at ASC
               LIMIT ? OFFSET ?""",
            (user_email, limit, offset)
        )
        rows = self.cursor.fetchall()

        messages = []
        for row in rows:
            messages.append({
                "id": row["id"],
                "role": row["role"],
                "content": row["content"],
                "sources": json.loads(row["sources"] or "[]"),
                "response_time": row["response_time"],
                "num_docs": row["num_docs"],
                "created_at": row["created_at"],
            })
        return messages

    def get_chat_message_count(self, user_email: str) -> int:
        """
        Đếm tổng số tin nhắn chat của user.

        Args:
            user_email: Email của user.

        Returns:
            Số lượng tin nhắn.
        """
        self.cursor.execute(
            "SELECT COUNT(*) as cnt FROM chat_messages WHERE user_email = ?",
            (user_email,)
        )
        return self.cursor.fetchone()["cnt"]

    def clear_chat_history(self, user_email: str) -> int:
        """
        Xóa toàn bộ lịch sử chat của user.

        Args:
            user_email: Email của user.

        Returns:
            Số tin nhắn đã xóa.
        """
        self.cursor.execute(
            "DELETE FROM chat_messages WHERE user_email = ?",
            (user_email,)
        )
        deleted = self.cursor.rowcount
        self.conn.commit()
        return deleted

    def close(self):
        """Đóng kết nối database."""
        if self.conn:
            self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
