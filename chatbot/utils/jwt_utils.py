"""
🔐 JWT Token Utilities.

Tạo và xác thực JWT tokens cho hệ thống đăng nhập.
"""

import os
from datetime import datetime, timedelta, timezone

import jwt

# Cấu hình JWT
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "chatbot-kinhte-default-secret-change-this")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24


def create_jwt_token(user_data: dict) -> str:
    """
    Tạo JWT token từ thông tin user.

    Args:
        user_data: Dict chứa thông tin user (email, name, picture, ...).

    Returns:
        JWT token string.
    """
    payload = {
        "sub": user_data.get("email", ""),
        "name": user_data.get("name", ""),
        "email": user_data.get("email", ""),
        "picture": user_data.get("picture", ""),
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def verify_jwt_token(token: str) -> dict | None:
    """
    Giải mã và xác thực JWT token.

    Args:
        token: JWT token string.

    Returns:
        Dict chứa payload nếu token hợp lệ, None nếu không hợp lệ hoặc hết hạn.
    """
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        print("⚠️ Token đã hết hạn.")
        return None
    except jwt.InvalidTokenError as e:
        print(f"⚠️ Token không hợp lệ: {e}")
        return None
