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
from app.root_admin import (
    ADMIN_LOGIN_ACCOUNT_KEY,
    ADMIN_LOGIN_PASSWORD_KEY,
    canonical_admin_email,
    hash_admin_password,
    is_admin_password_hash,
)

logger = get_logger(__name__)


# Database file path
DB_DIR = Path(__file__).parent.parent / "data"
DB_PATH = DB_DIR / "login_sessions.db"

# Session TTL (10 phút)
SESSION_TTL_MINUTES = 10
DEFAULT_FREE_TOKENS = 5
GUEST_DAILY_QUESTION_LIMIT = 5
GUEST_DAILY_TOKEN_LIMIT = 2000
PAYMENT_TTL_MINUTES = 5
ADMIN_EMAILS: set[str] = set()

APP_SETTING_DEFINITIONS = [
    {
        "key": "ENV",
        "default": "production",
        "is_secret": 0,
        "description": "Moi truong chay ung dung.",
    },
    {
        "key": "PORT",
        "default": "8001",
        "is_secret": 0,
        "description": "Port backend FastAPI.",
    },
    {
        "key": "ALLOW_ORIGINS",
        "default": "http://localhost:5173,http://localhost:8001",
        "is_secret": 0,
        "description": "Danh sach CORS origins, phan tach bang dau phay.",
    },
    {
        "key": "JWT_SECRET_KEY",
        "default": "__GENERATE_JWT_SECRET__",
        "is_secret": 1,
        "description": "Secret ky JWT, phai giu bi mat.",
    },
    {
        "key": "DEFAULT_FREE_TOKENS",
        "default": "100",
        "is_secret": 0,
        "description": "So credit hoi mien phi cap cho user moi.",
    },
    {
        "key": "MAX_QUESTION_CHARS",
        "default": "4000",
        "is_secret": 0,
        "description": "Do dai toi da cua cau hoi.",
    },
    {
        "key": "TASK_RESULT_TTL_SECONDS",
        "default": "600",
        "is_secret": 0,
        "description": "Thoi gian giu ket qua task async.",
    },
    {
        "key": "TASK_PROCESSING_TIMEOUT_SECONDS",
        "default": "1800",
        "is_secret": 0,
        "description": "Timeout cho task async dang xu ly.",
    },
    {
        "key": "TASK_CLEANUP_INTERVAL_SECONDS",
        "default": "60",
        "is_secret": 0,
        "description": "Chu ky cleanup task async.",
    },
    {
        "key": "LLM_TEMPERATURE",
        "default": "0",
        "is_secret": 0,
        "description": "Nhiet do sinh cau tra loi cua LLM.",
    },
    {
        "key": "ADMIN_LOGIN_EMAIL",
        "default": "admin@local",
        "is_secret": 0,
        "description": "Tai khoan dang nhap admin bang mat khau co dinh. Co the dung admin hoac email.",
    },
    {
        "key": "ADMIN_LOGIN_PASSWORD",
        "default": "admin123456",
        "is_secret": 1,
        "description": "Hash mat khau co dinh cho root admin password login.",
    },
    {
        "key": "DEFAULT_LLM",
        "default": "openai",
        "is_secret": 0,
        "description": "Nha cung cap LLM mac dinh: openai, gemini, groq.",
    },
    {
        "key": "KEY_API_OPENAI",
        "default": "",
        "is_secret": 1,
        "description": "OpenAI API key dung cho provider openai.",
    },
    {
        "key": "OPENAI_LLM_MODEL_NAME",
        "default": "gpt-5-mini",
        "is_secret": 0,
        "description": "Ten model OpenAI.",
    },
    {
        "key": "GOOGLE_API_KEY",
        "default": "",
        "is_secret": 1,
        "description": "Google Gemini API key.",
    },
    {
        "key": "GOOGLE_LLM_MODEL_NAME",
        "default": "gemini-2.5-flash",
        "is_secret": 0,
        "description": "Ten model Gemini.",
    },
    {
        "key": "GROQ_API_KEY",
        "default": "",
        "is_secret": 1,
        "description": "Groq API key.",
    },
    {
        "key": "GROQ_LLM_MODEL_NAME",
        "default": "llama-3.1-8b-instant",
        "is_secret": 0,
        "description": "Ten model Groq.",
    },
    {
        "key": "GOOGLE_CLIENT_ID",
        "default": "",
        "is_secret": 0,
        "description": "Google OAuth client id.",
    },
    {
        "key": "GOOGLE_CLIENT_SECRET",
        "default": "",
        "is_secret": 1,
        "description": "Google OAuth client secret.",
    },
    {
        "key": "OAUTH_REDIRECT_URI",
        "default": "http://localhost:8001/api/v1/auth/google/callback/flutter",
        "is_secret": 0,
        "description": "Google OAuth redirect URI.",
    },
    {
        "key": "NAME_WEB",
        "default": "KTChatbot",
        "is_secret": 0,
        "description": "Ma website dung trong noi dung chuyen khoan.",
    },
    {
        "key": "SEPAY_API_KEY",
        "default": "",
        "is_secret": 1,
        "description": "SePay API key de doc giao dich.",
    },
    {
        "key": "SEPAY_ACCOUNT_NUMBER",
        "default": "",
        "is_secret": 0,
        "description": "So tai khoan ngan hang lien ket SePay.",
    },
    {
        "key": "BANK_CODE",
        "default": "MB",
        "is_secret": 0,
        "description": "Ma ngan hang VietQR.",
    },
    {
        "key": "BANK_NAME",
        "default": "MB Bank",
        "is_secret": 0,
        "description": "Ten ngan hang hien thi.",
    },
    {
        "key": "BANK_ACCOUNT_NAME",
        "default": "",
        "is_secret": 0,
        "description": "Ten chu tai khoan hien thi tren QR.",
    },
]

APP_SETTING_KEYS = {item["key"] for item in APP_SETTING_DEFINITIONS}


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
        self.db_type = "sqlite"
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

        self._add_column_if_missing("users", "gravatar_url", "gravatar_url TEXT")
        self._add_column_if_missing("users", "is_admin", "is_admin INTEGER DEFAULT 0")

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

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                is_secret INTEGER DEFAULT 0,
                description TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_by TEXT
            )
        """)

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                actor_email TEXT,
                action TEXT NOT NULL,
                target_type TEXT,
                target_id TEXT,
                details TEXT DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at
            ON audit_logs(created_at, id)
        """)
        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_audit_logs_actor
            ON audit_logs(actor_email, created_at)
        """)

        for setting in APP_SETTING_DEFINITIONS:
            default_value = setting["default"]
            if setting["key"] == "JWT_SECRET_KEY" and default_value == "__GENERATE_JWT_SECRET__":
                default_value = f"{uuid4().hex}{uuid4().hex}"
            if setting["key"] == ADMIN_LOGIN_PASSWORD_KEY and default_value and not is_admin_password_hash(default_value):
                default_value = hash_admin_password(default_value)

            self.cursor.execute(f"""
                INSERT INTO app_settings (key, value, is_secret, description)
                VALUES ({self.P}, {self.P}, {self.P}, {self.P})
                ON CONFLICT(key) DO UPDATE SET
                    value = CASE
                        WHEN (app_settings.value IS NULL OR app_settings.value = '')
                             AND excluded.value IS NOT NULL
                             AND excluded.value != ''
                        THEN excluded.value
                        ELSE app_settings.value
                    END,
                    is_secret = excluded.is_secret,
                    description = excluded.description
            """, (
                setting["key"],
                default_value,
                setting["is_secret"],
                setting["description"],
            ))

        self._ensure_admin_password_hashed()
        self._ensure_root_admin_user()
        self._create_root_admin_triggers()
        self.conn.commit()

    def _root_admin_email_sql(self) -> str:
        return """
            COALESCE(
                (
                    SELECT CASE
                        WHEN value IS NULL OR trim(value) = '' THEN 'admin@local'
                        WHEN instr(lower(trim(value)), '@') > 0 THEN lower(trim(value))
                        ELSE lower(trim(value)) || '@local'
                    END
                    FROM app_settings
                    WHERE key = 'ADMIN_LOGIN_EMAIL'
                ),
                'admin@local'
            )
        """

    def _ensure_admin_password_hashed(self):
        self.cursor.execute(f"SELECT value FROM app_settings WHERE key = {self.P}", (ADMIN_LOGIN_PASSWORD_KEY,))
        row = self.cursor.fetchone()
        value = (row["value"] or "") if row else ""
        if value and not is_admin_password_hash(value):
            self.cursor.execute(f"""
                UPDATE app_settings
                SET value = {self.P}, updated_at = CURRENT_TIMESTAMP, updated_by = COALESCE(updated_by, 'system:migration')
                WHERE key = {self.P}
            """, (hash_admin_password(value), ADMIN_LOGIN_PASSWORD_KEY))

    def _ensure_root_admin_user(self):
        self.cursor.execute(f"SELECT value FROM app_settings WHERE key = {self.P}", (ADMIN_LOGIN_ACCOUNT_KEY,))
        row = self.cursor.fetchone()
        root_email = canonical_admin_email(row["value"] if row else "admin@local")
        gravatar = get_gravatar_url(root_email)
        self.cursor.execute(f"""
            INSERT INTO users (email, name, picture, gravatar_url, is_admin, last_login)
            VALUES ({self.P}, {self.P}, NULL, {self.P}, 1, CURRENT_TIMESTAMP)
            ON CONFLICT(email) DO UPDATE SET
                name = CASE WHEN users.name IS NULL OR users.name = '' THEN excluded.name ELSE users.name END,
                gravatar_url = excluded.gravatar_url,
                is_admin = 1
        """, (root_email, "Root Admin", gravatar))
        self.ensure_user_balance(root_email)

    def _create_root_admin_triggers(self):
        root_email_expr = self._root_admin_email_sql()
        self.cursor.execute(f"""
            CREATE TRIGGER IF NOT EXISTS trg_users_protect_root_admin_delete
            BEFORE DELETE ON users
            WHEN lower(OLD.email) = ({root_email_expr})
            BEGIN
                SELECT RAISE(ABORT, 'ROOT_ADMIN_LOCKED');
            END
        """)
        self.cursor.execute(f"""
            CREATE TRIGGER IF NOT EXISTS trg_users_protect_root_admin_identity
            BEFORE UPDATE OF email, is_admin ON users
            WHEN lower(OLD.email) = ({root_email_expr})
                 AND (lower(NEW.email) != lower(OLD.email) OR NEW.is_admin != 1)
            BEGIN
                SELECT RAISE(ABORT, 'ROOT_ADMIN_LOCKED');
            END
        """)

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
        normalized_email = email.strip().lower()
        gravatar = get_gravatar_url(normalized_email)
        # Nếu không có picture từ Google, dùng Gravatar
        final_picture = picture or gravatar
        is_admin = 1 if normalized_email in ADMIN_EMAILS else 0

        self.cursor.execute(f"""
            INSERT INTO users (email, name, picture, gravatar_url, is_admin, last_login)
            VALUES ({self.P}, {self.P}, {self.P}, {self.P}, {self.P}, CURRENT_TIMESTAMP)
            ON CONFLICT(email) DO UPDATE SET
                name = excluded.name,
                picture = excluded.picture,
                gravatar_url = excluded.gravatar_url,
                is_admin = CASE
                    WHEN users.is_admin = 1 OR excluded.is_admin = 1 THEN 1
                    ELSE users.is_admin
                END,
                last_login = CURRENT_TIMESTAMP
        """, (normalized_email, name, final_picture, gravatar, is_admin))
        self.conn.commit()

        self.ensure_user_balance(normalized_email)

        return self.get_user_by_email(normalized_email)

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

    def set_user_admin(self, email: str, is_admin: bool = True) -> dict | None:
        """Cap hoac go quyen admin cho user."""
        normalized_email = email.strip().lower()
        self.cursor.execute(f"""
            UPDATE users
            SET is_admin = {self.P}
            WHERE email = {self.P}
        """, (1 if is_admin else 0, normalized_email))
        self.conn.commit()
        return self.get_user_by_email(normalized_email)

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

    def save_free_chat_exchange(
        self,
        user_email: str,
        conversation_id: str,
        question: str,
        answer: str,
    ) -> dict | None:
        """Lưu exchange chào hỏi với token_used=0 và giữ nguyên balance."""
        if not self.get_conversation(user_email, conversation_id):
            return None

        balance = self.get_token_balance(user_email)
        user_message_id = self.save_chat_message(
            user_email=user_email,
            role="user",
            content=question,
            conversation_id=conversation_id,
            token_used=0,
        )
        bot_message_id = self.save_chat_message(
            user_email=user_email,
            role="bot",
            content=answer,
            sources=[],
            response_time=0.0,
            num_docs=0,
            conversation_id=conversation_id,
            token_used=0,
        )
        self.cursor.execute(f"""
            UPDATE conversations
            SET updated_at = CURRENT_TIMESTAMP
            WHERE id = {self.P} AND user_email = {self.P}
        """, (conversation_id, user_email))
        self.conn.commit()

        self.cursor.execute(f"SELECT * FROM chat_messages WHERE id = {self.P}", (user_message_id,))
        user_message = self._message_row_to_dict(self.cursor.fetchone())
        self.cursor.execute(f"SELECT * FROM chat_messages WHERE id = {self.P}", (bot_message_id,))
        bot_message = self._message_row_to_dict(self.cursor.fetchone())
        return {
            "token_used": 0,
            "balance": balance,
            "user_message": user_message,
            "bot_message": bot_message,
            "conversation": self.get_conversation(user_email, conversation_id),
        }

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
        actual_tokens = max(1, int(input_tokens) + int(output_tokens))
        billing_credits = 1
        sources_json = json.dumps(sources or [], ensure_ascii=False)

        try:
            self.conn.execute("BEGIN")
            self.cursor.execute(f"""
                UPDATE user_balances
                SET token_balance = token_balance - {self.P}, updated_at = CURRENT_TIMESTAMP
                WHERE user_email = {self.P} AND token_balance >= {self.P}
            """, (billing_credits, user_email, billing_credits))

            if self.cursor.rowcount == 0:
                self.conn.rollback()
                return None

            self.cursor.execute(f"""
                INSERT INTO token_transactions (user_email, delta, reason)
                VALUES ({self.P}, {self.P}, {self.P})
            """, (user_email, -billing_credits, f"chat:{conversation_id}:actual_tokens={actual_tokens}"))

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
                "token_used": billing_credits,
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

    def ensure_user_balance(self, user_email: str, initial_tokens: int | None = None) -> int:
        """Tạo balance mặc định cho user mới nếu chưa có."""
        if initial_tokens is None:
            initial_tokens = int(self.get_app_setting("DEFAULT_FREE_TOKENS", str(DEFAULT_FREE_TOKENS)) or DEFAULT_FREE_TOKENS)
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

    def _parse_payment_created_at(self, created_at: str | None) -> datetime | None:
        if not created_at:
            return None
        normalized = str(created_at).replace("Z", "+00:00")
        if "T" not in normalized:
            normalized = normalized.replace(" ", "T")
        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError:
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

    def get_payment_expires_at(self, payment: dict, ttl_minutes: int = PAYMENT_TTL_MINUTES) -> str | None:
        created_at = self._parse_payment_created_at(payment.get("created_at"))
        if not created_at:
            return None
        return (created_at + timedelta(minutes=ttl_minutes)).isoformat()

    def is_payment_expired(self, payment: dict, ttl_minutes: int = PAYMENT_TTL_MINUTES) -> bool:
        if payment.get("status") != "pending":
            return False
        created_at = self._parse_payment_created_at(payment.get("created_at"))
        if not created_at:
            return False
        return datetime.now(timezone.utc) >= created_at + timedelta(minutes=ttl_minutes)

    def delete_payment_record(self, payment_id: int) -> bool:
        self.cursor.execute(
            f"DELETE FROM payments WHERE id = {self.P} AND status = 'pending'",
            (payment_id,),
        )
        deleted = self.cursor.rowcount > 0
        self.conn.commit()
        return deleted

    def delete_expired_pending_payments(self, ttl_minutes: int = PAYMENT_TTL_MINUTES) -> int:
        self.cursor.execute(f"""
            DELETE FROM payments
            WHERE status = 'pending'
              AND datetime(created_at) <= datetime('now', {self.P})
        """, (f"-{int(ttl_minutes)} minutes",))
        deleted = self.cursor.rowcount
        self.conn.commit()
        return int(deleted or 0)

    def complete_payment_record(self, payment_id: int, sepay_tx_id: str) -> bool:
        """
        Mark payment completed và cộng token đúng một lần.
        Trả True nếu lần gọi này đã credit token, False nếu đã completed/trùng tx/không tồn tại.
        """
        payment = self.get_payment_record(payment_id)
        if not payment:
            return False
        if payment["status"] != "pending":
            return False

        tokens = int(payment.get("tokens") or 0)
        self.ensure_user_balance(payment["user_email"], initial_tokens=0)

        try:
            self.conn.execute("BEGIN")
            self.cursor.execute(f"""
                UPDATE payments
                SET status = 'completed', sepay_tx_id = {self.P}
                WHERE id = {self.P} AND status = 'pending'
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

    # ------------------------------------------------------------------
    # Runtime App Settings
    # ------------------------------------------------------------------

    def _mask_setting_value(self, value: str, key: str = "") -> str:
        if not value:
            return ""
        if key == ADMIN_LOGIN_PASSWORD_KEY:
            return "Đã cấu hình"
        if len(value) <= 8:
            return "****"
        return f"{value[:4]}****{value[-4:]}"

    def _setting_row_to_dict(self, row: sqlite3.Row, expose_secret_values: bool = False) -> dict:
        value = row["value"] or ""
        is_secret = bool(row["is_secret"])
        return {
            "key": row["key"],
            "value": value if expose_secret_values or not is_secret else "",
            "value_preview": self._mask_setting_value(value, row["key"]) if is_secret else value,
            "has_value": bool(value),
            "is_secret": is_secret,
            "description": row["description"],
            "updated_at": row["updated_at"],
            "updated_by": row["updated_by"],
        }

    def get_app_setting(self, key: str, default: str | None = None) -> str | None:
        """Lay gia tri setting runtime tu DB. Tra default neu key khong ton tai."""
        if key not in APP_SETTING_KEYS:
            return default
        self.cursor.execute(f"SELECT value FROM app_settings WHERE key = {self.P}", (key,))
        row = self.cursor.fetchone()
        if not row:
            return default
        return row["value"] if row["value"] is not None else ""

    def list_app_settings(self, expose_secret_values: bool = False) -> list[dict]:
        """Liet ke settings; secret chi tra preview tru khi expose_secret_values=True."""
        self.cursor.execute("""
            SELECT * FROM app_settings
            ORDER BY key ASC
        """)
        return [self._setting_row_to_dict(row, expose_secret_values) for row in self.cursor.fetchall()]

    def update_app_setting(self, key: str, value: str, updated_by: str = None) -> dict | None:
        """Cap nhat mot setting runtime trong whitelist APP_SETTING_KEYS."""
        if key not in APP_SETTING_KEYS:
            return None

        safe_value = "" if value is None else str(value)
        if key == ADMIN_LOGIN_PASSWORD_KEY and safe_value and not is_admin_password_hash(safe_value):
            safe_value = hash_admin_password(safe_value)

        self.cursor.execute(f"""
            UPDATE app_settings
            SET value = {self.P}, updated_at = CURRENT_TIMESTAMP, updated_by = {self.P}
            WHERE key = {self.P}
        """, (safe_value, updated_by, key))
        if key == ADMIN_LOGIN_PASSWORD_KEY:
            self._ensure_admin_password_hashed()
        if key == ADMIN_LOGIN_ACCOUNT_KEY:
            self._ensure_root_admin_user()
        self.conn.commit()

        self.cursor.execute(f"SELECT * FROM app_settings WHERE key = {self.P}", (key,))
        row = self.cursor.fetchone()
        return self._setting_row_to_dict(row) if row else None

    # ------------------------------------------------------------------
    # Audit Log
    # ------------------------------------------------------------------

    def record_audit_log(
        self,
        actor_email: str | None,
        action: str,
        target_type: str = "",
        target_id: str = "",
        details: dict | None = None,
    ) -> dict:
        """Ghi audit log cho thao tac quan tri quan trong."""
        safe_details = json.dumps(details or {}, ensure_ascii=False)
        self.cursor.execute(f"""
            INSERT INTO audit_logs (actor_email, action, target_type, target_id, details)
            VALUES ({self.P}, {self.P}, {self.P}, {self.P}, {self.P})
        """, (
            (actor_email or "system")[:255],
            action[:120],
            (target_type or "")[:80],
            (target_id or "")[:255],
            safe_details[:5000],
        ))
        audit_id = self.cursor.lastrowid
        self.conn.commit()
        self.cursor.execute(f"SELECT * FROM audit_logs WHERE id = {self.P}", (audit_id,))
        return self._audit_row_to_dict(self.cursor.fetchone())

    def _audit_row_to_dict(self, row: sqlite3.Row) -> dict:
        details_raw = row["details"] or "{}"
        try:
            details = json.loads(details_raw)
        except json.JSONDecodeError:
            details = {"raw": details_raw}
        return {
            "id": row["id"],
            "actor_email": row["actor_email"],
            "action": row["action"],
            "target_type": row["target_type"],
            "target_id": row["target_id"],
            "details": details,
            "created_at": row["created_at"],
        }

    def list_audit_logs(self, limit: int = 50, offset: int = 0) -> dict:
        """Liet ke audit log gan nhat cho admin."""
        safe_limit = min(max(int(limit), 1), 200)
        safe_offset = max(int(offset), 0)
        self.cursor.execute("SELECT COUNT(*) AS total FROM audit_logs")
        total = int(self.cursor.fetchone()["total"] or 0)
        self.cursor.execute(f"""
            SELECT * FROM audit_logs
            ORDER BY created_at DESC, id DESC
            LIMIT {self.P} OFFSET {self.P}
        """, (safe_limit, safe_offset))
        return {
            "logs": [self._audit_row_to_dict(row) for row in self.cursor.fetchall()],
            "total": total,
            "limit": safe_limit,
            "offset": safe_offset,
        }

    # ------------------------------------------------------------------
    # Admin Dashboard
    # ------------------------------------------------------------------

    def get_admin_daily_metrics(self, days: int = 14) -> list[dict]:
        """So lieu theo ngay cho bieu do admin."""
        safe_days = min(max(int(days), 1), 90)
        today = datetime.now(timezone.utc).date()
        start_date = today - timedelta(days=safe_days - 1)
        metrics = {
            (start_date + timedelta(days=index)).isoformat(): {
                "date": (start_date + timedelta(days=index)).isoformat(),
                "revenue_vnd": 0.0,
                "payment_tokens": 0,
                "manual_tokens": 0,
                "spent_tokens": 0,
                "completed_payments": 0,
                "questions": 0,
                "active_users": 0,
            }
            for index in range(safe_days)
        }

        self.cursor.execute(f"""
            SELECT
                date(created_at) AS metric_date,
                COALESCE(SUM(CASE WHEN status = 'completed' THEN amount_vnd ELSE 0 END), 0) AS revenue_vnd,
                COALESCE(SUM(CASE WHEN status = 'completed' THEN tokens ELSE 0 END), 0) AS payment_tokens,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) AS completed_payments
            FROM payments
            WHERE date(created_at) >= {self.P}
            GROUP BY date(created_at)
        """, (start_date.isoformat(),))
        for row in self.cursor.fetchall():
            day = row["metric_date"]
            if day in metrics:
                metrics[day]["revenue_vnd"] = float(row["revenue_vnd"] or 0)
                metrics[day]["payment_tokens"] = int(row["payment_tokens"] or 0)
                metrics[day]["completed_payments"] = int(row["completed_payments"] or 0)

        self.cursor.execute(f"""
            SELECT
                date(created_at) AS metric_date,
                COALESCE(SUM(CASE WHEN delta > 0 AND reason LIKE 'admin_topup:%' THEN delta ELSE 0 END), 0) AS manual_tokens,
                COALESCE(SUM(CASE WHEN delta < 0 THEN ABS(delta) ELSE 0 END), 0) AS spent_tokens
            FROM token_transactions
            WHERE date(created_at) >= {self.P}
            GROUP BY date(created_at)
        """, (start_date.isoformat(),))
        for row in self.cursor.fetchall():
            day = row["metric_date"]
            if day in metrics:
                metrics[day]["manual_tokens"] = int(row["manual_tokens"] or 0)
                metrics[day]["spent_tokens"] = int(row["spent_tokens"] or 0)

        self.cursor.execute(f"""
            SELECT
                date(created_at) AS metric_date,
                COUNT(*) AS questions,
                COUNT(DISTINCT user_email) AS active_users
            FROM chat_messages
            WHERE role = 'user' AND date(created_at) >= {self.P}
            GROUP BY date(created_at)
        """, (start_date.isoformat(),))
        for row in self.cursor.fetchall():
            day = row["metric_date"]
            if day in metrics:
                metrics[day]["questions"] = int(row["questions"] or 0)
                metrics[day]["active_users"] = int(row["active_users"] or 0)

        return [metrics[key] for key in sorted(metrics.keys())]

    def get_admin_summary(self, days: int = 14) -> dict:
        """Tong hop so lieu cho dashboard admin."""
        self.cursor.execute("SELECT COUNT(*) AS total_users FROM users")
        total_users = int(self.cursor.fetchone()["total_users"] or 0)

        self.cursor.execute("SELECT COALESCE(SUM(token_balance), 0) AS total_balance FROM user_balances")
        total_balance = int(self.cursor.fetchone()["total_balance"] or 0)

        self.cursor.execute("""
            SELECT
                COUNT(*) AS total_payments,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) AS completed_payments,
                SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) AS pending_payments,
                COALESCE(SUM(CASE WHEN status = 'completed' THEN amount_vnd ELSE 0 END), 0) AS completed_revenue_vnd,
                COALESCE(SUM(CASE WHEN status = 'completed' THEN tokens ELSE 0 END), 0) AS payment_tokens
            FROM payments
        """)
        payment_stats = dict(self.cursor.fetchone())

        self.cursor.execute("""
            SELECT COALESCE(SUM(delta), 0) AS manual_tokens
            FROM token_transactions
            WHERE delta > 0 AND reason LIKE 'admin_topup:%'
        """)
        manual_tokens = int(self.cursor.fetchone()["manual_tokens"] or 0)

        self.cursor.execute("""
            SELECT COALESCE(SUM(ABS(delta)), 0) AS spent_tokens
            FROM token_transactions
            WHERE delta < 0
        """)
        spent_tokens = int(self.cursor.fetchone()["spent_tokens"] or 0)

        self.cursor.execute(f"""
            SELECT id, user_email, amount_vnd, package_id, tokens, status, sepay_tx_id, created_at
            FROM payments
            ORDER BY created_at DESC, id DESC
            LIMIT {self.P}
        """, (8,))
        recent_payments = [dict(row) for row in self.cursor.fetchall()]

        self.cursor.execute(f"""
            SELECT id, user_email, delta, reason, related_payment_id, created_at
            FROM token_transactions
            ORDER BY created_at DESC, id DESC
            LIMIT {self.P}
        """, (8,))
        recent_transactions = [dict(row) for row in self.cursor.fetchall()]

        return {
            "total_users": total_users,
            "total_token_balance": total_balance,
            "total_payments": int(payment_stats.get("total_payments") or 0),
            "completed_payments": int(payment_stats.get("completed_payments") or 0),
            "pending_payments": int(payment_stats.get("pending_payments") or 0),
            "completed_revenue_vnd": float(payment_stats.get("completed_revenue_vnd") or 0),
            "payment_tokens": int(payment_stats.get("payment_tokens") or 0),
            "manual_tokens": manual_tokens,
            "spent_tokens": spent_tokens,
            "recent_payments": recent_payments,
            "recent_transactions": recent_transactions,
            "daily_metrics": self.get_admin_daily_metrics(days=days),
            "recent_audit_logs": self.list_audit_logs(limit=10)["logs"],
            "alerts": self.get_admin_alerts(),
        }

    def list_admin_users(self, limit: int = 100, offset: int = 0, search: str = "") -> dict:
        """Liet ke users kem token balance va thong ke su dung co ban."""
        safe_limit = min(max(int(limit), 1), 200)
        safe_offset = max(int(offset), 0)
        search = (search or "").strip().lower()

        where_sql = ""
        params: list = []
        if search:
            where_sql = f"WHERE LOWER(u.email) LIKE {self.P} OR LOWER(COALESCE(u.name, '')) LIKE {self.P}"
            pattern = f"%{search}%"
            params.extend([pattern, pattern])

        self.cursor.execute(f"""
            SELECT COUNT(*) AS total
            FROM users u
            {where_sql}
        """, params)
        total = int(self.cursor.fetchone()["total"] or 0)

        self.cursor.execute(f"""
            SELECT
                u.id,
                u.email,
                u.name,
                u.picture,
                u.is_admin,
                u.created_at,
                u.last_login,
                COALESCE(ub.token_balance, 0) AS token_balance,
                COALESCE((
                    SELECT SUM(CASE WHEN p.status = 'completed' THEN p.amount_vnd ELSE 0 END)
                    FROM payments p
                    WHERE p.user_email = u.email
                ), 0) AS completed_revenue_vnd,
                (
                    SELECT COUNT(*) FROM conversations c WHERE c.user_email = u.email
                ) AS conversation_count,
                (
                    SELECT COUNT(*) FROM chat_messages m WHERE m.user_email = u.email
                ) AS message_count
            FROM users u
            LEFT JOIN user_balances ub ON ub.user_email = u.email
            {where_sql}
            ORDER BY u.last_login DESC, u.id DESC
            LIMIT {self.P} OFFSET {self.P}
        """, params + [safe_limit, safe_offset])

        users = []
        for row in self.cursor.fetchall():
            item = dict(row)
            item["is_admin"] = bool(item.get("is_admin"))
            item["token_balance"] = int(item.get("token_balance") or 0)
            item["conversation_count"] = int(item.get("conversation_count") or 0)
            item["message_count"] = int(item.get("message_count") or 0)
            item["completed_revenue_vnd"] = float(item.get("completed_revenue_vnd") or 0)
            users.append(item)

        return {
            "users": users,
            "total": total,
            "limit": safe_limit,
            "offset": safe_offset,
        }

    def get_admin_user_detail(self, user_email: str) -> dict | None:
        """Chi tiet user cho admin: ledger, payments, conversations."""
        user = self.get_user_by_email(user_email)
        if not user:
            return None

        user["token_balance"] = self.get_token_balance(user_email)

        self.cursor.execute(f"""
            SELECT id, user_email, delta, reason, related_payment_id, created_at
            FROM token_transactions
            WHERE user_email = {self.P}
            ORDER BY created_at DESC, id DESC
            LIMIT {self.P}
        """, (user_email, 30))
        transactions = [dict(row) for row in self.cursor.fetchall()]

        self.cursor.execute(f"""
            SELECT id, user_email, amount_vnd, package_id, tokens, status, sepay_tx_id, created_at
            FROM payments
            WHERE user_email = {self.P}
            ORDER BY created_at DESC, id DESC
            LIMIT {self.P}
        """, (user_email, 20))
        payments = [dict(row) for row in self.cursor.fetchall()]

        self.cursor.execute(f"""
            SELECT id, user_email, title, created_at, updated_at
            FROM conversations
            WHERE user_email = {self.P}
            ORDER BY updated_at DESC
            LIMIT {self.P}
        """, (user_email, 20))
        conversations = [dict(row) for row in self.cursor.fetchall()]

        return {
            "user": user,
            "transactions": transactions,
            "payments": payments,
            "conversations": conversations,
        }

    def get_admin_alerts(self) -> list[dict]:
        """Canh bao van hanh co ban cho dashboard."""
        alerts: list[dict] = []
        for key in ("KEY_API_OPENAI", "SEPAY_API_KEY", "SEPAY_ACCOUNT_NUMBER", "JWT_SECRET_KEY"):
            value = self.get_app_setting(key, "") or ""
            if not value.strip():
                alerts.append({
                    "severity": "critical" if key in ("KEY_API_OPENAI", "JWT_SECRET_KEY") else "warning",
                    "code": f"MISSING_{key}",
                    "message": f"{key} chưa được cấu hình.",
                })

        self.cursor.execute("SELECT COUNT(*) AS cnt FROM user_balances WHERE token_balance < 0")
        negative_users = int(self.cursor.fetchone()["cnt"] or 0)
        if negative_users:
            alerts.append({"severity": "critical", "code": "NEGATIVE_TOKEN_BALANCE", "message": f"{negative_users} tài khoản có token âm."})

        self.cursor.execute("""
            SELECT COUNT(*) AS cnt
            FROM payments
            WHERE status = 'pending' AND datetime(created_at) < datetime('now', '-5 minutes')
        """)
        stale_payments = int(self.cursor.fetchone()["cnt"] or 0)
        if stale_payments:
            alerts.append({"severity": "warning", "code": "STALE_PAYMENTS", "message": f"{stale_payments} payment pending quá 5 phút, cần được dọn."})

        return alerts

    def credit_user_tokens(self, user_email: str, tokens: int, reason: str, admin_email: str) -> dict | None:
        """Cong token cho user tu admin dashboard."""
        user = self.get_user_by_email(user_email)
        if not user:
            return None

        token_count = max(1, int(tokens))
        safe_reason = (reason or "admin_topup").strip()[:160] or "admin_topup"
        safe_admin = (admin_email or "admin").strip()[:160]
        ledger_reason = f"admin_topup:{safe_admin}:{safe_reason}"

        self.ensure_user_balance(user_email, initial_tokens=0)
        try:
            self.conn.execute("BEGIN")
            self.cursor.execute(f"""
                UPDATE user_balances
                SET token_balance = token_balance + {self.P}, updated_at = CURRENT_TIMESTAMP
                WHERE user_email = {self.P}
            """, (token_count, user_email))
            self.cursor.execute(f"""
                INSERT INTO token_transactions (user_email, delta, reason)
                VALUES ({self.P}, {self.P}, {self.P})
            """, (user_email, token_count, ledger_reason))
            transaction_id = self.cursor.lastrowid
            balance = self.get_token_balance(user_email, ensure=False)
            self.conn.commit()

            self.cursor.execute(f"SELECT * FROM token_transactions WHERE id = {self.P}", (transaction_id,))
            transaction = dict(self.cursor.fetchone())
            return {
                "user_email": user_email,
                "token_balance": balance,
                "transaction": transaction,
            }
        except Exception:
            self.conn.rollback()
            raise

    def close(self):
        """Đóng kết nối database."""
        if self.conn:
            self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
