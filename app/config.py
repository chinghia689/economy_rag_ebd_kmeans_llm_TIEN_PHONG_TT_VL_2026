"""
Quản lý cấu hình ứng dụng từ file .env.
Sử dụng dotenv để load biến môi trường.

Tham chiếu: docs/DOCS-main/skill_env_configuration.md
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Tìm file .env từ thư mục gốc dự án
_env_path = Path(__file__).parent.parent / ".env"
load_dotenv(_env_path)

WEAK_JWT_SECRETS = {
    "change-this-in-production",
    "chatbot-kinhte-default-secret-change-this",
    "thay-doi-key-nay-khi-deploy-production",
}


def _resolve_env() -> str:
    return os.getenv("ENV", "production").strip().lower()


def _resolve_jwt_secret(env: str) -> str:
    secret = os.getenv("JWT_SECRET_KEY", "").strip()
    is_production = env in {"production", "prod"}

    if is_production:
        if not secret:
            raise RuntimeError("JWT_SECRET_KEY is required when ENV=production.")
        if secret in WEAK_JWT_SECRETS or len(secret) < 32:
            raise RuntimeError(
                "JWT_SECRET_KEY must be a non-default value with at least 32 characters "
                "when ENV=production."
            )

    return secret or "dev-only-insecure-jwt-secret-change-before-production"


class Settings:
    """
    Cấu hình chung cho toàn bộ ứng dụng.
    DIR_ROOT được xác định từ vị trí file .env để tránh lỗi đường dẫn tương đối.
    """

    # Thư mục gốc của dự án (dựa trên vị trí file .env)
    DIR_ROOT: str = str(Path(__file__).parent.parent)

    # Môi trường: development hoặc production
    ENV: str = _resolve_env()

    # AI Engine
    DEFAULT_LLM: str = os.getenv("DEFAULT_LLM", "openai")
    KEY_API_OPENAI: str = os.getenv("KEY_API_OPENAI", "")
    OPENAI_LLM_MODEL_NAME: str = os.getenv("OPENAI_LLM_MODEL_NAME", "gpt-4o-mini")
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    GOOGLE_LLM_MODEL_NAME: str = os.getenv("GOOGLE_LLM_MODEL_NAME", "gemini-2.5-flash")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")

    # JWT
    JWT_SECRET_KEY: str = _resolve_jwt_secret(ENV)

    # Google OAuth
    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
    OAUTH_REDIRECT_URI: str = os.getenv(
        "OAUTH_REDIRECT_URI",
        "http://localhost:8001/api/v1/auth/google/callback/flutter"
    )

    # CORS
    ALLOW_ORIGINS: list = os.getenv(
        "ALLOW_ORIGINS", "http://localhost:5173,http://localhost:8001"
    ).split(",")

    # Payment (SePay + VietQR)
    NAME_WEB: str = os.getenv("NAME_WEB", "KTChatbot")
    SEPAY_API_KEY: str = os.getenv("SEPAY_API_KEY", "")
    SEPAY_ACCOUNT_NUMBER: str = os.getenv("SEPAY_ACCOUNT_NUMBER", "")
    BANK_CODE: str = os.getenv("BANK_CODE", "MB")
    BANK_NAME: str = os.getenv("BANK_NAME", "MB Bank")
    BANK_ACCOUNT_NAME: str = os.getenv("BANK_ACCOUNT_NAME", "")


settings = Settings()
