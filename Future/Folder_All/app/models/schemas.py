"""
Các Pydantic Schema chuẩn cho API Response.
Mỗi Endpoint phải trả về ApiSuccess hoặc ApiError.

Tham chiếu: docs/DOCS-main/skill_api_response_standard.md
"""

from pydantic import BaseModel
from typing import Any, Optional, List


class ApiSuccess(BaseModel):
    """
    Wrapper chuẩn cho mỗi response thành công.
    Frontend luôn kiểm tra success=True trước khi đọc data.
    """
    success: bool = True
    message: str = "Thành công"
    data: Optional[Any] = None


class ApiError(BaseModel):
    """
    Wrapper chuẩn cho mỗi response lỗi.
    Dùng kèm với HTTPException hoặc Exception handler.
    """
    success: bool = False
    message: str
    error_code: Optional[str] = None


class PaginatedData(BaseModel):
    """
    Wrapper cho các API có phân trang (list users, list transactions...).
    """
    items: List[Any]
    total: int
    page: int
    page_size: int
    total_pages: int
