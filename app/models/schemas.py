"""
Cac Pydantic Schema chuan cho API Response.
Moi Endpoint phai tra ve ApiSuccess hoac ApiError.

Tham chieu: docs/DOCS-main/skill_api_response_standard.md
"""

from pydantic import BaseModel
from typing import Any, Optional, List


class ApiSuccess(BaseModel):
    """
    Wrapper chuan cho moi response thanh cong.
    Frontend luon kiem tra success=True truoc khi doc data.
    """
    success: bool = True
    message: str = "Thanh cong"
    data: Optional[Any] = None


class ApiError(BaseModel):
    """
    Wrapper chuan cho moi response loi.
    Dung kem voi HTTPException hoac Exception handler.
    """
    success: bool = False
    message: str
    error_code: Optional[str] = None


class PaginatedData(BaseModel):
    """
    Wrapper cho cac API co phan trang (list users, list transactions...).
    """
    items: List[Any]
    total: int
    page: int
    page_size: int
    total_pages: int
