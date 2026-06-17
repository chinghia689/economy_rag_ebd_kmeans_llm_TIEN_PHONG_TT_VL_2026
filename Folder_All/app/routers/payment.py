"""
Payment Router cho SePay Polling.
Tham chieu: docs/DOCS-main/skill_payment_polling_sync.md
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.models.schemas import ApiSuccess, ApiError
from app.security.security import get_current_user
from chatbot.utils.base_db import UserDB
from app.utils.sepay_helper import encode_payment_id, check_sepay_transaction, make_vietqr_url
from app.runtime_config import get_runtime_settings

router = APIRouter(prefix="/payment", tags=["Payment"])

PAYMENT_TTL_SECONDS = 5 * 60

PAYMENT_PACKAGES = {
    "basic": {"tokens": 100, "amount": 30000},
    "pro": {"tokens": 500, "amount": 120000},
    "premium": {"tokens": 1200, "amount": 250000},
}


class PaymentCreateReq(BaseModel):
    package_id: str = Field(..., min_length=1)


def get_payment_package(package_id: str) -> dict[str, int]:
    package = PAYMENT_PACKAGES.get(package_id)
    if not package:
        raise HTTPException(
            status_code=400,
            detail=ApiError(
                message="Gói thanh toán không hợp lệ.",
                error_code="INVALID_PAYMENT_PACKAGE"
            ).model_dump()
        )
    return package


@router.post("/create")
async def create_payment(req: PaymentCreateReq, current_user: dict = Depends(get_current_user)):
    """Tao phien giao dich thanh toan."""
    email = current_user.get("email")
    if not email:
        raise HTTPException(
            status_code=401,
            detail=ApiError(message="Vui lòng đăng nhập.", error_code="UNAUTHORIZED").model_dump()
        )

    package = get_payment_package(req.package_id)
    amount = float(package["amount"])

    with UserDB() as db:
        db.delete_expired_pending_payments()
        # Tao record pending trong DB
        payment_id = db.create_payment_record(
            user_email=email,
            amount=amount,
            package_id=req.package_id,
            tokens=package["tokens"],
        )
        payment = db.get_payment_record(payment_id)
        expires_at = db.get_payment_expires_at(payment) if payment else None

    if not payment_id:
        raise HTTPException(
            status_code=500,
            detail=ApiError(message="Lỗi hệ thống khi tạo giao dịch.", error_code="PAYMENT_CREATE_ERROR").model_dump()
        )

    payment_config = get_runtime_settings({
        "NAME_WEB": "KTChatbot",
        "SEPAY_ACCOUNT_NUMBER": "",
        "BANK_NAME": "MB Bank",
        "BANK_ACCOUNT_NAME": "",
    })
    hex_id = encode_payment_id(payment_id)
    content = f"{payment_config['NAME_WEB']}NAPTOKEN{hex_id}"
    qr_url = make_vietqr_url(int(amount), content)

    return ApiSuccess(data={
        "payment_id": payment_id,
        "hex_id": hex_id,
        "transfer_content": content,
        "amount": amount,
        "package_id": req.package_id,
        "tokens": package["tokens"],
        "qr_url": qr_url,
        "bank_account": payment_config["SEPAY_ACCOUNT_NUMBER"],
        "bank_name": payment_config["BANK_NAME"],
        "account_name": payment_config["BANK_ACCOUNT_NAME"],
        "expires_at": expires_at,
        "expires_in_seconds": PAYMENT_TTL_SECONDS,
    })

@router.get("/status/{payment_id}")
async def check_payment_status(payment_id: int, current_user: dict = Depends(get_current_user)):
    """Polling kiem tra trang thai giao dich tu SePay."""
    email = current_user.get("email")
    
    with UserDB() as db:
        payment = db.get_payment_record(payment_id)
        
        if not payment:
            raise HTTPException(
                status_code=404,
                detail=ApiError(message="Giao dịch không tồn tại.", error_code="PAYMENT_NOT_FOUND").model_dump()
            )

        if payment["user_email"] != email:
            raise HTTPException(
                status_code=403,
                detail=ApiError(message="Bạn không có quyền xem giao dịch này.", error_code="FORBIDDEN").model_dump()
            )
            
        if payment["status"] == "completed":
            return ApiSuccess(data={
                "status": "completed",
                "token_balance": db.get_token_balance(email),
            })

        if db.is_payment_expired(payment):
            db.delete_payment_record(payment_id)
            return ApiSuccess(
                message="Giao dịch đã quá 5 phút và đã bị xóa.",
                data={"status": "expired"},
            )
            
        # Neu van dang pending -> Check SePay
        is_paid, sepay_tx_id = check_sepay_transaction(payment_id, payment["amount_vnd"])
        
        if is_paid:
            # Cap nhat status va cong token idempotent
            credited = db.complete_payment_record(payment_id, str(sepay_tx_id))
            payment = db.get_payment_record(payment_id)
            if not credited and payment and payment["status"] != "completed":
                raise HTTPException(
                    status_code=409,
                    detail=ApiError(
                        message="Giao dịch ngân hàng đã được dùng cho payment khác.",
                        error_code="DUPLICATE_PAYMENT_TRANSACTION"
                    ).model_dump()
                )
            return ApiSuccess(data={
                "status": "completed",
                "token_balance": db.get_token_balance(email),
            })
            
        return ApiSuccess(data={"status": "pending", "expires_at": db.get_payment_expires_at(payment)})
