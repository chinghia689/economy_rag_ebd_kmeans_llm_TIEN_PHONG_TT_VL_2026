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

Tham chiếu: docs/DOCS-main/skill_security_authentication.md Mục 1, 3, 7.
"""

from fastapi import Depends, HTTPException, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext

from chatbot.utils.jwt_utils import verify_jwt_token
from chatbot.utils.base_db import UserDB
from app.models.schemas import ApiError
from app.logger import get_logger

logger = get_logger(__name__)

# FastAPI Security scheme cho Swagger UI
security_scheme = HTTPBearer(auto_error=False)

# Bcrypt context cho hash mat khau (skill_security_authentication.md Muc 7)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ------------------------------------------------------------------
# Password Hashing (skill_security_authentication.md Muc 7)
# ------------------------------------------------------------------

def hash_password(plain_password: str) -> str:
    """
    Ma hoa mat khau truoc khi luu vao DB.
    bcrypt tu dong them 'salt' ngau nhien vao moi lan hash.

    Args:
        plain_password: Mat khau dang plain text.

    Returns:
        Chuoi hash bcrypt.
    """
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    So sanh mat khau nguoi dung nhap voi hash trong DB.

    Args:
        plain_password: Mat khau nguoi dung nhap.
        hashed_password: Hash bcrypt da luu trong DB.

    Returns:
        True neu khop, False neu sai.
    """
    return pwd_context.verify(plain_password, hashed_password)


# ------------------------------------------------------------------
# JWT Dependency: get_current_user
# ------------------------------------------------------------------

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
) -> dict:
    """
    FastAPI Dependency: Xac thuc JWT token va tra ve thong tin user.

    Luong xu ly:
        1. Giai ma JWT token tu Authorization header.
        2. Truy van lai DB de dam bao user chua bi xoa hoac doi quyen.
        3. Tra ve dict chua thong tin user.

    Args:
        credentials: Bearer token tu Authorization header.

    Returns:
        Dict chua thong tin user tu database.

    Raises:
        HTTPException 401: Neu token thieu, het han, hoac user khong ton tai.
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

    # Luon truy van lai DB de dam bao user chua bi xoa hoac doi quyen
    with UserDB() as db:
        user = db.get_user_by_email(email)

    if not user:
        raise HTTPException(
            status_code=401,
            detail=ApiError(
                message="Phiên đăng nhập không còn hợp lệ. Vui lòng đăng nhập lại.",
                error_code="USER_NOT_FOUND"
            ).model_dump()
        )

    return user


# ------------------------------------------------------------------
# RBAC Dependency: get_current_admin
# ------------------------------------------------------------------

def get_current_admin(
    current_user: dict = Depends(get_current_user),
) -> dict:
    """
    FastAPI Dependency: Kiem tra quyen admin.
    Ke thua tu get_current_user (Lop bao ve 2 - RBAC).

    Args:
        current_user: User da xac thuc tu get_current_user.

    Returns:
        Dict chua thong tin admin user.

    Raises:
        HTTPException 403: Neu user khong phai admin.
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
