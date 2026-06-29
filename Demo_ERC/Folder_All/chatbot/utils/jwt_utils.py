"""
JWT Token Utilities.

Tạo và xác thực JWT tokens cho hệ thống đăng nhập.
"""

from datetime import datetime, timedelta, timezone

import jwt

from app.logger import get_logger
from app.runtime_config import get_runtime_setting

logger = get_logger(__name__)

JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24
DEFAULT_DEV_JWT_SECRET = "dev-only-insecure-jwt-secret-change-before-production"


def get_jwt_secret() -> str:
    """Read JWT secret from DB-backed runtime settings."""
    secret = get_runtime_setting("JWT_SECRET_KEY", DEFAULT_DEV_JWT_SECRET).strip()
    return secret or DEFAULT_DEV_JWT_SECRET


def create_jwt_token(user_data: dict) -> str:
    """
    Tạo JWT token từ thông tin user.
    """
    payload = {
        "sub": user_data.get("email", ""),
        "name": user_data.get("name", ""),
        "email": user_data.get("email", ""),
        "picture": user_data.get("picture", ""),
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS),
    }
    return jwt.encode(payload, get_jwt_secret(), algorithm=JWT_ALGORITHM)


def verify_jwt_token(token: str) -> dict | None:
    """
    Giải mã và xác thực JWT token.
    """
    try:
        payload = jwt.decode(token, get_jwt_secret(), algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("Token đã hết hạn.")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Token không hợp lệ: {e}")
        return None
