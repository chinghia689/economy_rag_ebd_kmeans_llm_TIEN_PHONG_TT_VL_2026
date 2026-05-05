"""
Security module - JWT verification & RBAC (Role-Based Access Control).

Cung cấp 2 FastAPI Dependency:
    - get_current_user: Xác thực JWT, trả về thông tin user.
    - get_current_admin: Kiểm tra quyền admin (kế thừa từ get_current_user).

Sử dụng:
    @router.get("/protected")
    async def protected_route(user: dict = Depends(get_current_user)):
        # user đã được xác thực

    @router.delete("/admin/users/{id}")
    async def admin_route(admin: dict = Depends(get_current_admin)):
        # admin đã được xác thực + kiểm tra quyền

Tham chiếu: docs/DOCS-main/skill_security_authentication.md Mục 1 & 3.
"""

from fastapi import Depends, HTTPException, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from chatbot.utils.jwt_utils import verify_jwt_token
from chatbot.utils.base_db import UserDB
from app.models.schemas import ApiError
from app.logger import get_logger

logger = get_logger(__name__)

# FastAPI Security scheme cho Swagger UI
security_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
) -> dict:
    """
    FastAPI Dependency: Xác thực JWT token và trả về thông tin user.

    Luồng xử lý:
        1. Giải mã JWT token từ Authorization header.
        2. Truy vấn lại DB để đảm bảo user chưa bị xóa hoặc đổi quyền.
        3. Trả về dict chứa thông tin user.

    Args:
        credentials: Bearer token từ Authorization header.

    Returns:
        Dict chứa thông tin user từ database.

    Raises:
        HTTPException 401: Nếu token thiếu, hết hạn, hoặc user không tồn tại.
    """
    if not credentials:
        raise HTTPException(
            status_code=401,
            detail=ApiError(
                message="Vui lòng đăng nhập.",
                error_code="MISSING_TOKEN"
            ).model_dump()
        )

    token = credentials.credentials
    payload = verify_jwt_token(token)

    if not payload:
        raise HTTPException(
            status_code=401,
            detail=ApiError(
                message="Token không hợp lệ hoặc đã hết hạn.",
                error_code="INVALID_TOKEN"
            ).model_dump()
        )

    email = payload.get("email")
    if not email:
        raise HTTPException(
            status_code=401,
            detail=ApiError(
                message="Token không chứa thông tin email.",
                error_code="INVALID_TOKEN_PAYLOAD"
            ).model_dump()
        )

    # Luôn truy vấn lại DB để đảm bảo user chưa bị xóa hoặc đổi quyền
    with UserDB() as db:
        user = db.get_user_by_email(email)

    if not user:
        # User tồn tại trong token nhưng không có trong DB
        # Có thể do user mới đăng nhập lần đầu qua Google
        # Tạo user từ payload token
        logger.warning(f"User {email} không tìm thấy trong DB, tạo mới từ token.")
        with UserDB() as db:
            user = db.upsert_user(
                email=email,
                name=payload.get("name"),
                picture=payload.get("picture"),
            )

    return user


def get_current_admin(
    current_user: dict = Depends(get_current_user),
) -> dict:
    """
    FastAPI Dependency: Kiểm tra quyền admin.
    Kế thừa từ get_current_user (Lớp bảo vệ 2 - RBAC).

    Args:
        current_user: User đã xác thực từ get_current_user.

    Returns:
        Dict chứa thông tin admin user.

    Raises:
        HTTPException 403: Nếu user không phải admin.
    """
    if not current_user.get("is_admin"):
        raise HTTPException(
            status_code=403,
            detail=ApiError(
                message="Bạn không có quyền thực hiện thao tác này.",
                error_code="FORBIDDEN"
            ).model_dump()
        )
    return current_user
