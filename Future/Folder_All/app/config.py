"""Compatibility settings object backed by database runtime settings.

New code should use app.runtime_config directly. This module exists so old imports of
`from app.config import settings` do not depend on .env at import time.
"""

from pathlib import Path

from app.runtime_config import get_runtime_setting


class Settings:
    DIR_ROOT: str = str(Path(__file__).parent.parent)

    @property
    def ENV(self) -> str:
        return get_runtime_setting("ENV", "production").strip().lower()

    @property
    def DEFAULT_LLM(self) -> str:
        return get_runtime_setting("DEFAULT_LLM", "openai")

    @property
    def KEY_API_OPENAI(self) -> str:
        return get_runtime_setting("KEY_API_OPENAI", "")

    @property
    def OPENAI_LLM_MODEL_NAME(self) -> str:
        return get_runtime_setting("OPENAI_LLM_MODEL_NAME", "gpt-5-mini")

    @property
    def GOOGLE_API_KEY(self) -> str:
        return get_runtime_setting("GOOGLE_API_KEY", "")

    @property
    def GOOGLE_LLM_MODEL_NAME(self) -> str:
        return get_runtime_setting("GOOGLE_LLM_MODEL_NAME", "gemini-2.5-flash")

    @property
    def GROQ_API_KEY(self) -> str:
        return get_runtime_setting("GROQ_API_KEY", "")

    @property
    def GROQ_LLM_MODEL_NAME(self) -> str:
        return get_runtime_setting("GROQ_LLM_MODEL_NAME", "llama-3.1-8b-instant")

    @property
    def JWT_SECRET_KEY(self) -> str:
        return get_runtime_setting("JWT_SECRET_KEY", "")

    @property
    def GOOGLE_CLIENT_ID(self) -> str:
        return get_runtime_setting("GOOGLE_CLIENT_ID", "")

    @property
    def GOOGLE_CLIENT_SECRET(self) -> str:
        return get_runtime_setting("GOOGLE_CLIENT_SECRET", "")

    @property
    def OAUTH_REDIRECT_URI(self) -> str:
        return get_runtime_setting("OAUTH_REDIRECT_URI", "http://localhost:8001/api/v1/auth/google/callback/flutter")

    @property
    def ALLOW_ORIGINS(self) -> list[str]:
        raw = get_runtime_setting("ALLOW_ORIGINS", "http://localhost:5173,http://localhost:8001")
        return [origin.strip() for origin in raw.split(",") if origin.strip()]

    @property
    def NAME_WEB(self) -> str:
        return get_runtime_setting("NAME_WEB", "KTChatbot")

    @property
    def SEPAY_API_KEY(self) -> str:
        return get_runtime_setting("SEPAY_API_KEY", "")

    @property
    def SEPAY_ACCOUNT_NUMBER(self) -> str:
        return get_runtime_setting("SEPAY_ACCOUNT_NUMBER", "")

    @property
    def BANK_CODE(self) -> str:
        return get_runtime_setting("BANK_CODE", "MB")

    @property
    def BANK_NAME(self) -> str:
        return get_runtime_setting("BANK_NAME", "MB Bank")

    @property
    def BANK_ACCOUNT_NAME(self) -> str:
        return get_runtime_setting("BANK_ACCOUNT_NAME", "")


settings = Settings()
