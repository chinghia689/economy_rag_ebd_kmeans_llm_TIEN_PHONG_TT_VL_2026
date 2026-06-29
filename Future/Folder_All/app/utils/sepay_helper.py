"""
Helper module cho SePay API va ma hoa Payment ID.
Tham chieu: docs/DOCS-main/skill_payment_polling_sync.md
"""

import re
from urllib.parse import quote

import requests

from app.logger import get_logger
from app.runtime_config import get_runtime_settings

logger = get_logger(__name__)

SEPAY_BASE_URL = "https://my.sepay.vn/userapi/transactions/list"
SECRET_XOR_KEY = 0x5EAFB  # Thay doi key nay cho moi du an


def _payment_config() -> dict[str, str]:
    return get_runtime_settings({
        "SEPAY_API_KEY": "",
        "SEPAY_ACCOUNT_NUMBER": "",
        "BANK_CODE": "MB",
        "BANK_ACCOUNT_NAME": "",
        "NAME_WEB": "KTChatbot",
    })


def make_vietqr_url(amount: int, transfer_content: str) -> str:
    """Tạo URL ảnh VietQR (chuẩn NAPAS) để hiển thị QR chuyển khoản."""
    cfg = _payment_config()
    return (
        f"https://img.vietqr.io/image/{cfg['BANK_CODE']}"
        f"-{cfg['SEPAY_ACCOUNT_NUMBER']}-compact.png"
        f"?amount={amount}"
        f"&addInfo={quote(transfer_content)}"
        f"&accountName={quote(cfg['BANK_ACCOUNT_NAME'])}"
    )


def encode_payment_id(p_id: int) -> str:
    """Ma hoa ID hoa don sang HEX an toan."""
    return hex(p_id ^ SECRET_XOR_KEY)[2:].upper()


def decode_payment_id(hex_str: str) -> int:
    """Giai ma HEX tro lai ID hoa don."""
    return int(hex_str, 16) ^ SECRET_XOR_KEY


def get_last_transactions(limit: int = 20) -> list:
    """
    Goi SePay API de lay danh sach giao dich gan nhat.

    Args:
        limit: So luong giao dich can lay (mac dinh 20).

    Returns:
        list: Danh sach cac giao dich dang dict.
    """
    cfg = _payment_config()
    if not cfg["SEPAY_API_KEY"]:
        logger.warning("SEPAY_API_KEY khong duoc cau hinh.")
        return []

    headers = {
        "Authorization": f"Bearer {cfg['SEPAY_API_KEY']}",
        "Content-Type": "application/json",
    }
    params = {
        "account_number": cfg["SEPAY_ACCOUNT_NUMBER"],
        "limit": limit,
    }

    try:
        response = requests.get(SEPAY_BASE_URL, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get("transactions", [])
    except requests.RequestException as e:
        logger.error(f"Loi goi SePay API: {e}")
        return []


def check_sepay_transaction(payment_id: int, amount_vnd: float) -> tuple[bool, str | None]:
    """
    Kiem tra lich su SePay xem co giao dich nao khop khong.
    """
    target_hex = encode_payment_id(payment_id)
    cfg = _payment_config()
    prefix = cfg["NAME_WEB"] + "NAPTOKEN"
    pattern = rf"{prefix}([A-Fa-f0-9]+)"

    history = get_last_transactions()

    for tx in history:
        content = tx.get("transaction_content", "") or tx.get("content", "")
        amount = float(tx.get("amount_in", 0))

        # Kiem tra noi dung chua ma nap
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            found_hex = match.group(1).upper()
            if found_hex == target_hex and amount >= amount_vnd:
                return True, tx.get("id")

    return False, None
