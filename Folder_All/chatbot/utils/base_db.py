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
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from app.logger import get_logger

logger = get_logger(__name__)


# Database file path
DB_DIR = Path(__file__).parent.parent / "data"
DB_PATH = DB_DIR / "login_sessions.db"

# Session TTL (10 phút)
SESSION_TTL_MINUTES = 10
DEFAULT_FREE_TOKENS = int(os.getenv("DEFAULT_FREE_TOKENS", "100"))
GUEST_DAILY_QUESTION_LIMIT = int(os.getenv("GUEST_DAILY_QUESTION_LIMIT", "5"))
GUEST_DAILY_TOKEN_LIMIT = int(os.getenv("GUEST_DAILY_TOKEN_LIMIT", "2000"))


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

        # SQL Compatibility (skill_sql_compatibility.md)
        self.db_type = os.getenv("DB_TYPE", "sqlite")
        self.P = "?" if self.db_type == "sqlite" else "%s"

        # Đảm bảo thư mục tồn tại
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()

        # Tạo bảng nếu chưa có
        self._create_tables()

    def _table_columns(self, table_name: str) -> set[str]:
        self.cursor.execute(f"PRAGMA table_info({table_name})")
        return {row["name"] for row in self.cursor.fetchall()}

    def _add_column_if_missing(self, table_name: str, column_name: str, column_sql: str):
        if column_name not in self._table_columns(table_name):
            self.cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_sql}")

    def _create_tables(self):
        """Tạo bảng login_sessions, users, conversations, balances và chat_messages nếu chưa tồn tại."""
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
                conversation_id TEXT,
                user_email TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('user', 'bot')),
                content TEXT NOT NULL,
                sources TEXT DEFAULT '[]',
                token_used INTEGER DEFAULT 0,
                response_time REAL,
                num_docs INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        self._add_column_if_missing("chat_messages", "conversation_id", "conversation_id TEXT")
        self._add_column_if_missing("chat_messages", "token_used", "token_used INTEGER DEFAULT 0")

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                user_email TEXT NOT NULL,
                title TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Index cho truy van nhanh theo user_email
        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_chat_user_email 
            ON chat_messages(user_email)
        """)
        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_chat_conversation_id
            ON chat_messages(conversation_id)
        """)
        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_conversations_user_email
            ON conversations(user_email, updated_at)
        """)

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_balances (
                user_email TEXT PRIMARY KEY,
                token_balance INTEGER NOT NULL DEFAULT 0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS token_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_email TEXT NOT NULL,
                delta INTEGER NOT NULL,
                reason TEXT NOT NULL,
                related_payment_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_token_transactions_user_email
            ON token_transactions(user_email, created_at)
        """)

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS guest_usage (
                guest_key TEXT NOT NULL,
                usage_date TEXT NOT NULL,
                question_count INTEGER NOT NULL DEFAULT 0,
                token_used INTEGER NOT NULL DEFAULT 0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (guest_key, usage_date)
            )
        """)

        # Bảng payments (SePay integration)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_email TEXT NOT NULL,
                amount_vnd REAL NOT NULL,
                package_id TEXT,
                tokens INTEGER DEFAULT 0,
                status TEXT DEFAULT 'pending',
                sepay_tx_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        self._add_column_if_missing("payments", "tokens", "tokens INTEGER DEFAULT 0")
        try:
            self.cursor.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_payments_sepay_tx_id_unique
                ON payments(sepay_tx_id)
                WHERE sepay_tx_id IS NOT NULL AND sepay_tx_id != ''
            """)
        except sqlite3.IntegrityError:
            logger.warning("Khong the tao unique index cho sepay_tx_id vi dang co du lieu trung.")

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

        self.cursor.execute(f"""
            INSERT INTO users (email, name, picture, gravatar_url, last_login)
            VALUES ({self.P}, {self.P}, {self.P}, {self.P}, CURRENT_TIMESTAMP)
            ON CONFLICT(email) DO UPDATE SET
                name = excluded.name,
                picture = excluded.picture,
                gravatar_url = excluded.gravatar_url,
                last_login = CURRENT_TIMESTAMP
        """, (email, name, final_picture, gravatar))
        self.conn.commit()

        self.ensure_user_balance(email)

        return self.get_user_by_email(email)

    def get_user_by_email(self, email: str) -> dict | None:
        """
        Lấy thông tin user theo email.

        Args:
            email: Email của user.

        Returns:
            Dict chứa thông tin user hoặc None.
        """
        self.cursor.execute(f"SELECT * FROM users WHERE email = {self.P}", (email,))
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
                f"INSERT INTO login_sessions (session_id, status) VALUES ({self.P}, 'pending')",
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
            f"SELECT * FROM login_sessions WHERE session_id = {self.P}",
            (session_id,)
        )
        row = self.cursor.fetchone()

        if not row:
            return None

        # Kiểm tra TTL
        created_at = datetime.fromisoformat(row["created_at"]).replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) - created_at > timedelta(minutes=SESSION_TTL_MINUTES):
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
        self.cursor.execute(f"""
               UPDATE login_sessions
               SET token = {self.P}, status = 'completed',
                   user_email = {self.P}, user_name = {self.P}, user_picture = {self.P}
               WHERE session_id = {self.P}""",
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
            f"DELETE FROM login_sessions WHERE session_id = {self.P}",
            (session_id,)
        )
        self.conn.commit()
        return self.cursor.rowcount > 0

    def cleanup_old_sessions(self):
        """
        Xóa tất cả sessions cũ hơn TTL (10 phút).
        Được gọi tự động mỗi khi tạo session mới để giữ DB sạch.
        """
        cutoff = (datetime.now(timezone.utc) - timedelta(minutes=SESSION_TTL_MINUTES)).isoformat()
        self.cursor.execute(
            f"DELETE FROM login_sessions WHERE created_at < {self.P}",
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
                          num_docs: int = 0, conversation_id: str = None,
                          token_used: int = 0) -> int:
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

        self.cursor.execute(f"""
            INSERT INTO chat_messages
            (conversation_id, user_email, role, content, sources, token_used, response_time, num_docs)
            VALUES ({self.P}, {self.P}, {self.P}, {self.P}, {self.P}, {self.P}, {self.P}, {self.P})""",
            (conversation_id, user_email, role, content, sources_json, token_used, response_time, num_docs)
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
        self.cursor.execute(f"""
            SELECT * FROM chat_messages
            WHERE user_email = {self.P}
            ORDER BY created_at ASC
            LIMIT {self.P} OFFSET {self.P}""",
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
            f"SELECT COUNT(*) as cnt FROM chat_messages WHERE user_email = {self.P}",
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
            f"DELETE FROM chat_messages WHERE user_email = {self.P}",
            (user_email,)
        )
        deleted = self.cursor.rowcount
        self.conn.commit()
        return deleted

    # ------------------------------------------------------------------
    # Conversation Management
    # ------------------------------------------------------------------

    def _conversation_row_to_dict(self, row: sqlite3.Row) -> dict:
        return {
            "id": row["id"],
            "user_email": row["user_email"],
            "title": row["title"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def _message_row_to_dict(self, row: sqlite3.Row) -> dict:
        return {
            "id": row["id"],
            "conversation_id": row["conversation_id"],
            "user_email": row["user_email"],
            "role": row["role"],
            "content": row["content"],
            "sources": json.loads(row["sources"] or "[]"),
            "token_used": row["token_used"] or 0,
            "response_time": row["response_time"],
            "num_docs": row["num_docs"],
            "created_at": row["created_at"],
        }

    def create_conversation(self, user_email: str, title: str = None) -> dict:
        """Tạo cuộc hội thoại mới cho một user."""
        conversation_id = str(uuid4())
        safe_title = (title or "Cuộc hội thoại mới").strip()[:120] or "Cuộc hội thoại mới"

        self.cursor.execute(f"""
            INSERT INTO conversations (id, user_email, title)
            VALUES ({self.P}, {self.P}, {self.P})
        """, (conversation_id, user_email, safe_title))
        self.conn.commit()
        return self.get_conversation(user_email, conversation_id)

    def get_conversation(self, user_email: str, conversation_id: str) -> dict | None:
        """Lấy một cuộc hội thoại nếu thuộc user."""
        self.cursor.execute(f"""
            SELECT * FROM conversations
            WHERE id = {self.P} AND user_email = {self.P}
        """, (conversation_id, user_email))
        row = self.cursor.fetchone()
        return self._conversation_row_to_dict(row) if row else None

    def list_conversations(self, user_email: str, limit: int = 100, offset: int = 0) -> list[dict]:
        """Liệt kê cuộc hội thoại của user, mới nhất trước."""
        self.cursor.execute(f"""
            SELECT * FROM conversations
            WHERE user_email = {self.P}
            ORDER BY updated_at DESC
            LIMIT {self.P} OFFSET {self.P}
        """, (user_email, limit, offset))
        return [self._conversation_row_to_dict(row) for row in self.cursor.fetchall()]

    def update_conversation_title(self, user_email: str, conversation_id: str, title: str) -> dict | None:
        """Đổi tiêu đề cuộc hội thoại nếu thuộc user."""
        safe_title = title.strip()[:120]
        if not safe_title:
            return self.get_conversation(user_email, conversation_id)

        self.cursor.execute(f"""
            UPDATE conversations
            SET title = {self.P}, updated_at = CURRENT_TIMESTAMP
            WHERE id = {self.P} AND user_email = {self.P}
        """, (safe_title, conversation_id, user_email))
        self.conn.commit()
        return self.get_conversation(user_email, conversation_id)

    def delete_conversation(self, user_email: str, conversation_id: str) -> bool:
        """Xóa conversation và messages thuộc user."""
        self.cursor.execute(f"""
            DELETE FROM chat_messages
            WHERE conversation_id = {self.P} AND user_email = {self.P}
        """, (conversation_id, user_email))
        self.cursor.execute(f"""
            DELETE FROM conversations
            WHERE id = {self.P} AND user_email = {self.P}
        """, (conversation_id, user_email))
        deleted = self.cursor.rowcount > 0
        self.conn.commit()
        return deleted

    def get_conversation_messages(self, user_email: str, conversation_id: str) -> list[dict] | None:
        """Lấy messages của conversation nếu thuộc user."""
        if not self.get_conversation(user_email, conversation_id):
            return None

        self.cursor.execute(f"""
            SELECT * FROM chat_messages
            WHERE conversation_id = {self.P} AND user_email = {self.P}
            ORDER BY created_at ASC, id ASC
        """, (conversation_id, user_email))
        return [self._message_row_to_dict(row) for row in self.cursor.fetchall()]

    def save_chat_exchange_and_debit(
        self,
        user_email: str,
        conversation_id: str,
        question: str,
        answer: str,
        sources: list,
        response_time: float,
        num_docs: int,
        input_tokens: int,
        output_tokens: int,
    ) -> dict | None:
        """
        Lưu user/bot messages và trừ balance trong cùng transaction.
        Trả None nếu conversation không thuộc user hoặc không đủ token.
        """
        if not self.get_conversation(user_email, conversation_id):
            return None

        self.ensure_user_balance(user_email)
        total_tokens = max(1, int(input_tokens) + int(output_tokens))
        sources_json = json.dumps(sources or [], ensure_ascii=False)

        try:
            self.conn.execute("BEGIN")
            self.cursor.execute(f"""
                UPDATE user_balances
                SET token_balance = token_balance - {self.P}, updated_at = CURRENT_TIMESTAMP
                WHERE user_email = {self.P} AND token_balance >= {self.P}
            """, (total_tokens, user_email, total_tokens))

            if self.cursor.rowcount == 0:
                self.conn.rollback()
                return None

            self.cursor.execute(f"""
                INSERT INTO token_transactions (user_email, delta, reason)
                VALUES ({self.P}, {self.P}, {self.P})
            """, (user_email, -total_tokens, f"chat:{conversation_id}"))

            self.cursor.execute(f"""
                INSERT INTO chat_messages
                (conversation_id, user_email, role, content, token_used)
                VALUES ({self.P}, {self.P}, 'user', {self.P}, {self.P})
            """, (conversation_id, user_email, question, input_tokens))
            user_message_id = self.cursor.lastrowid

            self.cursor.execute(f"""
                INSERT INTO chat_messages
                (conversation_id, user_email, role, content, sources, token_used, response_time, num_docs)
                VALUES ({self.P}, {self.P}, 'bot', {self.P}, {self.P}, {self.P}, {self.P}, {self.P})
            """, (
                conversation_id, user_email, answer, sources_json,
                output_tokens, response_time, num_docs
            ))
            bot_message_id = self.cursor.lastrowid

            title = question.replace("\n", " ").strip()
            if title:
                self.cursor.execute(f"""
                    UPDATE conversations
                    SET title = CASE
                            WHEN title = 'Cuộc hội thoại mới' THEN {self.P}
                            ELSE title
                        END,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = {self.P} AND user_email = {self.P}
                """, (title[:40], conversation_id, user_email))
            else:
                self.cursor.execute(f"""
                    UPDATE conversations
                    SET updated_at = CURRENT_TIMESTAMP
                    WHERE id = {self.P} AND user_email = {self.P}
                """, (conversation_id, user_email))

            self.cursor.execute(f"SELECT * FROM chat_messages WHERE id = {self.P}", (user_message_id,))
            user_message = self._message_row_to_dict(self.cursor.fetchone())
            self.cursor.execute(f"SELECT * FROM chat_messages WHERE id = {self.P}", (bot_message_id,))
            bot_message = self._message_row_to_dict(self.cursor.fetchone())
            balance = self.get_token_balance(user_email, ensure=False)

            self.conn.commit()
            return {
                "token_used": total_tokens,
                "balance": balance,
                "user_message": user_message,
                "bot_message": bot_message,
                "conversation": self.get_conversation(user_email, conversation_id),
            }
        except Exception:
            self.conn.rollback()
            raise

    # ------------------------------------------------------------------
    # Token Balance / Ledger
    # ------------------------------------------------------------------

    def ensure_user_balance(self, user_email: str, initial_tokens: int = DEFAULT_FREE_TOKENS) -> int:
        """Tạo balance mặc định cho user mới nếu chưa có."""
        self.cursor.execute(f"""
            INSERT OR IGNORE INTO user_balances (user_email, token_balance)
            VALUES ({self.P}, {self.P})
        """, (user_email, int(initial_tokens)))
        self.conn.commit()
        return self.get_token_balance(user_email, ensure=False)

    def get_token_balance(self, user_email: str, ensure: bool = True) -> int:
        """Lấy token balance hiện tại."""
        if ensure:
            self.ensure_user_balance(user_email)

        self.cursor.execute(
            f"SELECT token_balance FROM user_balances WHERE user_email = {self.P}",
            (user_email,)
        )
        row = self.cursor.fetchone()
        return int(row["token_balance"]) if row else 0

    def get_token_transactions(self, user_email: str, limit: int = 50) -> list[dict]:
        """Lấy ledger token gần nhất."""
        self.cursor.execute(f"""
            SELECT * FROM token_transactions
            WHERE user_email = {self.P}
            ORDER BY created_at DESC, id DESC
            LIMIT {self.P}
        """, (user_email, limit))
        return [dict(row) for row in self.cursor.fetchall()]

    def debit_user_tokens(self, user_email: str, token_count: int, reason: str) -> int | None:
        """Trừ token nếu đủ balance. Trả balance mới hoặc None nếu không đủ."""
        token_count = max(1, int(token_count))
        self.ensure_user_balance(user_email)
        try:
            self.conn.execute("BEGIN")
            self.cursor.execute(f"""
                UPDATE user_balances
                SET token_balance = token_balance - {self.P}, updated_at = CURRENT_TIMESTAMP
                WHERE user_email = {self.P} AND token_balance >= {self.P}
            """, (token_count, user_email, token_count))
            if self.cursor.rowcount == 0:
                self.conn.rollback()
                return None

            self.cursor.execute(f"""
                INSERT INTO token_transactions (user_email, delta, reason)
                VALUES ({self.P}, {self.P}, {self.P})
            """, (user_email, -token_count, reason))
            balance = self.get_token_balance(user_email, ensure=False)
            self.conn.commit()
            return balance
        except Exception:
            self.conn.rollback()
            raise

    # ------------------------------------------------------------------
    # Guest Usage
    # ------------------------------------------------------------------

    def get_guest_usage(self, guest_key: str, usage_date: str = None) -> dict:
        usage_date = usage_date or datetime.now(timezone.utc).date().isoformat()
        self.cursor.execute(f"""
            SELECT * FROM guest_usage
            WHERE guest_key = {self.P} AND usage_date = {self.P}
        """, (guest_key, usage_date))
        row = self.cursor.fetchone()
        if row:
            return dict(row)
        return {
            "guest_key": guest_key,
            "usage_date": usage_date,
            "question_count": 0,
            "token_used": 0,
        }

    def record_guest_usage(self, guest_key: str, token_used: int, usage_date: str = None) -> dict:
        usage_date = usage_date or datetime.now(timezone.utc).date().isoformat()
        self.cursor.execute(f"""
            INSERT INTO guest_usage (guest_key, usage_date, question_count, token_used)
            VALUES ({self.P}, {self.P}, 1, {self.P})
            ON CONFLICT(guest_key, usage_date) DO UPDATE SET
                question_count = question_count + 1,
                token_used = token_used + excluded.token_used,
                updated_at = CURRENT_TIMESTAMP
        """, (guest_key, usage_date, int(token_used)))
        self.conn.commit()
        return self.get_guest_usage(guest_key, usage_date)

    # ------------------------------------------------------------------
    # Payment Management (SePay)
    # ------------------------------------------------------------------

    def create_payment_record(self, user_email: str, amount: float, package_id: str, tokens: int = 0) -> int:
        """Tao don hang moi."""
        self.cursor.execute(f"""
            INSERT INTO payments (user_email, amount_vnd, package_id, tokens)
            VALUES ({self.P}, {self.P}, {self.P}, {self.P})
        """, (user_email, amount, package_id, int(tokens)))
        self.conn.commit()
        return self.cursor.lastrowid

    def get_payment_record(self, payment_id: int) -> dict | None:
        """Lay thong tin don hang."""
        self.cursor.execute(f"SELECT * FROM payments WHERE id = {self.P}", (payment_id,))
        row = self.cursor.fetchone()
        return dict(row) if row else None

    def complete_payment_record(self, payment_id: int, sepay_tx_id: str) -> bool:
        """
        Mark payment completed và cộng token đúng một lần.
        Trả True nếu lần gọi này đã credit token, False nếu đã completed/trùng tx/không tồn tại.
        """
        payment = self.get_payment_record(payment_id)
        if not payment:
            return False
        if payment["status"] == "completed":
            return False

        tokens = int(payment.get("tokens") or 0)
        self.ensure_user_balance(payment["user_email"], initial_tokens=0)

        try:
            self.conn.execute("BEGIN")
            self.cursor.execute(f"""
                UPDATE payments
                SET status = 'completed', sepay_tx_id = {self.P}
                WHERE id = {self.P} AND status != 'completed'
            """, (sepay_tx_id, payment_id))

            if self.cursor.rowcount == 0:
                self.conn.rollback()
                return False

            if tokens > 0:
                self.cursor.execute(f"""
                    UPDATE user_balances
                    SET token_balance = token_balance + {self.P}, updated_at = CURRENT_TIMESTAMP
                    WHERE user_email = {self.P}
                """, (tokens, payment["user_email"]))
                self.cursor.execute(f"""
                    INSERT INTO token_transactions
                    (user_email, delta, reason, related_payment_id)
                    VALUES ({self.P}, {self.P}, {self.P}, {self.P})
                """, (payment["user_email"], tokens, "payment", payment_id))

            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            self.conn.rollback()
            logger.warning(f"SePay transaction {sepay_tx_id} da duoc gan voi payment khac.")
            return False

    def close(self):
        """Đóng kết nối database."""
        if self.conn:
            self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
