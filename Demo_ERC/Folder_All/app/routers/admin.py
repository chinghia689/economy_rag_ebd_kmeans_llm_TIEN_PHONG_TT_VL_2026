"""Admin APIs for user balances, payment stats, and runtime settings."""

import csv
import io
import re

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.models.schemas import ApiSuccess, ApiError
from app.root_admin import (
    ADMIN_LOGIN_ACCOUNT_KEY,
    ADMIN_LOGIN_PASSWORD_KEY,
    canonical_admin_email,
    is_root_admin_email,
)
from app.public_content import PUBLIC_CONTENT_SETTING_KEYS
from app.security.security import get_current_admin
from chatbot.utils.base_db import UserDB

router = APIRouter(prefix="/admin", tags=["Admin"])

ROOT_ADMIN_SETTING_KEYS = {ADMIN_LOGIN_ACCOUNT_KEY, ADMIN_LOGIN_PASSWORD_KEY}

ADMIN_VISIBLE_SETTING_KEYS = {
    "ENV",
    "PORT",
    "ALLOW_ORIGINS",
    "JWT_SECRET_KEY",
    "DEFAULT_FREE_TOKENS",
    "MAX_QUESTION_CHARS",
    "TASK_RESULT_TTL_SECONDS",
    "TASK_PROCESSING_TIMEOUT_SECONDS",
    "TASK_CLEANUP_INTERVAL_SECONDS",
    "LLM_TEMPERATURE",
    "ADMIN_LOGIN_EMAIL",
    "ADMIN_LOGIN_PASSWORD",
    "KEY_API_OPENAI",
    "OPENAI_LLM_MODEL_NAME",
    "GOOGLE_CLIENT_ID",
    "GOOGLE_CLIENT_SECRET",
    "OAUTH_REDIRECT_URI",
    "NAME_WEB",
    "SEPAY_API_KEY",
    "SEPAY_ACCOUNT_NUMBER",
    "BANK_CODE",
    "BANK_NAME",
    "BANK_ACCOUNT_NAME",
} | PUBLIC_CONTENT_SETTING_KEYS


class TokenTopUpReq(BaseModel):
    tokens: int = Field(..., gt=0, le=10_000_000)
    reason: str = Field("admin_topup", max_length=160)


class AdminRoleUpdateReq(BaseModel):
    is_admin: bool = True


class SettingUpdateReq(BaseModel):
    value: str = Field("", max_length=10000)


class SettingsBulkUpdateReq(BaseModel):
    settings: dict[str, str] = Field(default_factory=dict)


class ReadOnlySqlReq(BaseModel):
    query: str = Field(..., min_length=1, max_length=5000)
    limit: int = Field(100, ge=1, le=500)



def admin_email(admin: dict) -> str:
    return (admin.get("email") or "admin").strip().lower()


def root_admin_email(db: UserDB) -> str:
    return canonical_admin_email(db.get_app_setting(ADMIN_LOGIN_ACCOUNT_KEY, "admin@local"))


def current_admin_is_root(db: UserDB, admin: dict) -> bool:
    return is_root_admin_email(admin_email(admin), db.get_app_setting(ADMIN_LOGIN_ACCOUNT_KEY, "admin@local"))


def require_root_admin(db: UserDB, admin: dict):
    if current_admin_is_root(db, admin):
        return
    raise HTTPException(
        status_code=403,
        detail=ApiError(
            message="Chỉ root admin hiện tại mới được đổi tài khoản hoặc mật khẩu admin cao nhất.",
            error_code="ROOT_ADMIN_REQUIRED",
        ).model_dump(),
    )



def quote_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def normalize_readonly_query(query: str) -> str:
    stripped = query.strip()
    if stripped.endswith(';'):
        stripped = stripped[:-1].strip()
    if ';' in stripped:
        raise HTTPException(
            status_code=400,
            detail=ApiError(message="Chỉ cho phép một câu SQL mỗi lần.", error_code="MULTI_STATEMENT_SQL").model_dump(),
        )
    lowered = stripped.lower()
    if not (lowered.startswith('select ') or lowered.startswith('pragma ')):
        raise HTTPException(
            status_code=400,
            detail=ApiError(
                message="SQL viewer chỉ cho phép SELECT hoặc PRAGMA read-only.",
                error_code="READ_ONLY_SQL_ONLY",
            ).model_dump(),
        )
    if re.search(r"\bapp_settings\b", lowered) and not lowered.startswith('pragma table_info'):
        raise HTTPException(
            status_code=400,
            detail=ApiError(
                message="Không cho query raw app_settings để tránh lộ secret API key. Dùng tab Cấu hình API để xem/sửa.",
                error_code="APP_SETTINGS_QUERY_BLOCKED",
            ).model_dump(),
        )
    return stripped


@router.get("/summary")
async def get_admin_summary(days: int = Query(14, ge=1, le=90), admin: dict = Depends(get_current_admin)):
    """Return dashboard stats for deposits, tokens, and recent ledger activity."""
    with UserDB() as db:
        return ApiSuccess(data=db.get_admin_summary(days=days))


@router.get("/users")
async def list_admin_users(
    limit: int = Query(100, ge=1, le=200),
    offset: int = Query(0, ge=0),
    search: str = Query(""),
    admin: dict = Depends(get_current_admin),
):
    """Return child/user accounts with balances and usage counters."""
    with UserDB() as db:
        return ApiSuccess(data=db.list_admin_users(limit=limit, offset=offset, search=search))


@router.get("/users/{user_email}/detail")
async def get_admin_user_detail(
    user_email: str,
    admin: dict = Depends(get_current_admin),
):
    """Return one user detail with token/payment/conversation history."""
    with UserDB() as db:
        detail = db.get_admin_user_detail(user_email.strip().lower())

    if not detail:
        raise HTTPException(
            status_code=404,
            detail=ApiError(message="Tài khoản không tồn tại.", error_code="USER_NOT_FOUND").model_dump(),
        )

    return ApiSuccess(data=detail)


@router.delete("/users/{user_email}")
async def delete_admin_user(
    user_email: str,
    admin: dict = Depends(get_current_admin),
):
    """Delete a user account and permanently block its email."""
    normalized_email = user_email.strip().lower()
    current_admin_email = admin_email(admin)
    if normalized_email == current_admin_email:
        raise HTTPException(
            status_code=400,
            detail=ApiError(
                message="Không thể tự xóa tài khoản admin đang đăng nhập.",
                error_code="CANNOT_DELETE_SELF",
            ).model_dump(),
        )

    with UserDB() as db:
        try:
            deleted = db.delete_user_account(normalized_email, deleted_by=current_admin_email)
        except PermissionError:
            raise HTTPException(
                status_code=400,
                detail=ApiError(
                    message="Không thể xóa tài khoản root admin.",
                    error_code="ROOT_ADMIN_LOCKED",
                ).model_dump(),
            )
        if deleted:
            db.record_audit_log(
                actor_email=current_admin_email,
                action="user.account.deleted_by_admin",
                target_type="user",
                target_id=normalized_email,
                details={"email_permanently_blocked": True},
            )

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail=ApiError(
                message="Tài khoản không tồn tại.",
                error_code="USER_NOT_FOUND",
            ).model_dump(),
        )

    return ApiSuccess(
        message="Đã xóa tài khoản và chặn email đăng nhập lại.",
        data={"deleted": True, "email_blocked": True},
    )


@router.patch("/users/{user_email}/admin")
async def update_user_admin_role(
    user_email: str,
    req: AdminRoleUpdateReq,
    admin: dict = Depends(get_current_admin),
):
    """Grant or revoke admin permission for a user account."""
    normalized_email = user_email.strip().lower()
    current_admin_email = (admin.get("email") or "").strip().lower()

    if normalized_email == current_admin_email and not req.is_admin:
        raise HTTPException(
            status_code=400,
            detail=ApiError(
                message="Không thể tự gỡ quyền admin của chính mình.",
                error_code="CANNOT_DEMOTE_SELF",
            ).model_dump(),
        )

    with UserDB() as db:
        if normalized_email == root_admin_email(db) and not req.is_admin:
            raise HTTPException(
                status_code=400,
                detail=ApiError(
                    message="Không thể gỡ quyền admin của root admin.",
                    error_code="ROOT_ADMIN_LOCKED",
                ).model_dump(),
            )
        user = db.set_user_admin(normalized_email, req.is_admin)
        if user:
            db.record_audit_log(
                actor_email=admin_email(admin),
                action="user.admin_role.updated",
                target_type="user",
                target_id=normalized_email,
                details={"is_admin": req.is_admin},
            )

    if not user:
        raise HTTPException(
            status_code=404,
            detail=ApiError(
                message="Tài khoản không tồn tại.",
                error_code="USER_NOT_FOUND",
            ).model_dump(),
        )

    return ApiSuccess(
        message="Đã cập nhật quyền admin.",
        data={"user": user},
    )


@router.post("/users/{user_email}/tokens")
async def top_up_user_tokens(
    user_email: str,
    req: TokenTopUpReq,
    admin: dict = Depends(get_current_admin),
):
    """Credit tokens to a user account from the admin dashboard."""
    with UserDB() as db:
        result = db.credit_user_tokens(
            user_email=user_email,
            tokens=req.tokens,
            reason=req.reason,
            admin_email=admin_email(admin),
        )
        if result:
            db.record_audit_log(
                actor_email=admin_email(admin),
                action="user.tokens.credited",
                target_type="user",
                target_id=user_email.strip().lower(),
                details={"tokens": req.tokens, "reason": req.reason, "transaction_id": result["transaction"]["id"]},
            )

    if not result:
        raise HTTPException(
            status_code=404,
            detail=ApiError(
                message="Tài khoản không tồn tại.",
                error_code="USER_NOT_FOUND",
            ).model_dump(),
        )

    return ApiSuccess(message="Đã nạp credit cho tài khoản.", data=result)


@router.get("/settings")
async def list_admin_settings(admin: dict = Depends(get_current_admin)):
    """List editable runtime settings. Secret values are masked by default."""
    with UserDB() as db:
        settings = [
            setting for setting in db.list_app_settings(expose_secret_values=False)
            if setting["key"] in ADMIN_VISIBLE_SETTING_KEYS
        ]
        return ApiSuccess(data={"settings": settings})


@router.put("/settings/{key}")
async def update_admin_setting(
    key: str,
    req: SettingUpdateReq,
    admin: dict = Depends(get_current_admin),
):
    """Update one runtime setting."""
    with UserDB() as db:
        if key in ROOT_ADMIN_SETTING_KEYS:
            require_root_admin(db, admin)
        setting = db.update_app_setting(key, req.value, updated_by=admin_email(admin))
        if setting:
            db.record_audit_log(
                actor_email=admin_email(admin),
                action="setting.updated",
                target_type="app_setting",
                target_id=key,
                details={"key": key, "is_secret": bool(setting.get("is_secret")), "has_value": bool(req.value)},
            )

    if not setting:
        raise HTTPException(
            status_code=404,
            detail=ApiError(
                message="Cấu hình không hợp lệ.",
                error_code="SETTING_NOT_FOUND",
            ).model_dump(),
        )

    return ApiSuccess(message="Đã cập nhật cấu hình.", data={"setting": setting})


@router.patch("/settings")
async def bulk_update_admin_settings(
    req: SettingsBulkUpdateReq,
    admin: dict = Depends(get_current_admin),
):
    """Update several runtime settings at once."""
    updated = []
    invalid = []
    with UserDB() as db:
        if any(key in ROOT_ADMIN_SETTING_KEYS for key in req.settings):
            require_root_admin(db, admin)
        for key, value in req.settings.items():
            setting = db.update_app_setting(key, value, updated_by=admin_email(admin))
            if setting:
                updated.append(setting)
            else:
                invalid.append(key)
        if updated:
            db.record_audit_log(
                actor_email=admin_email(admin),
                action="settings.bulk_updated",
                target_type="app_settings",
                target_id="bulk",
                details={"keys": [item["key"] for item in updated], "count": len(updated)},
            )

    if invalid:
        raise HTTPException(
            status_code=400,
            detail=ApiError(
                message=f"Cấu hình không hợp lệ: {', '.join(invalid)}",
                error_code="INVALID_SETTINGS",
            ).model_dump(),
        )

    return ApiSuccess(message="Đã cập nhật cấu hình.", data={"settings": updated})

@router.get("/audit-logs")
async def list_audit_logs(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    admin: dict = Depends(get_current_admin),
):
    """List recent admin audit events."""
    with UserDB() as db:
        return ApiSuccess(data=db.list_audit_logs(limit=limit, offset=offset))


@router.get("/export/transactions.csv")
async def export_transactions_csv(admin: dict = Depends(get_current_admin)):
    """Export recent credit transactions as CSV."""
    with UserDB() as db:
        db.cursor.execute("""
            SELECT id, user_email, delta, reason, related_payment_id, created_at
            FROM token_transactions
            ORDER BY created_at DESC, id DESC
            LIMIT 5000
        """)
        rows = [dict(row) for row in db.cursor.fetchall()]
        db.record_audit_log(
            actor_email=admin_email(admin),
            action="export.transactions_csv",
            target_type="token_transactions",
            target_id="csv",
            details={"rows": len(rows)},
        )

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["id", "user_email", "delta", "reason", "related_payment_id", "created_at"])
    writer.writeheader()
    writer.writerows(rows)
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=credit_transactions.csv"},
    )


@router.get("/database/tables")
async def list_database_tables(admin: dict = Depends(get_current_admin)):
    """List SQLite tables and columns for admin inspection."""
    with UserDB() as db:
        db.cursor.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name ASC
        """)
        tables = []
        for row in db.cursor.fetchall():
            name = row["name"]
            db.cursor.execute(f"PRAGMA table_info({quote_identifier(name)})")
            columns = [
                {
                    "name": col["name"],
                    "type": col["type"],
                    "notnull": bool(col["notnull"]),
                    "primary_key": bool(col["pk"]),
                }
                for col in db.cursor.fetchall()
            ]
            db.cursor.execute(f"SELECT COUNT(*) AS cnt FROM {quote_identifier(name)}")
            row_count = int(db.cursor.fetchone()["cnt"] or 0)
            tables.append({"name": name, "row_count": row_count, "columns": columns})

    return ApiSuccess(data={"tables": tables})


@router.post("/database/query")
async def run_readonly_sql(req: ReadOnlySqlReq, admin: dict = Depends(get_current_admin)):
    """Run one read-only SQL query against SQLite."""
    query = normalize_readonly_query(req.query)
    limited_query = query
    if query.lower().startswith('select ') and not re.search(r"\blimit\s+\d+", query, re.IGNORECASE):
        limited_query = f"{query} LIMIT {req.limit}"

    with UserDB() as db:
        try:
            db.cursor.execute(limited_query)
            rows = db.cursor.fetchall()
        except Exception as exc:
            raise HTTPException(
                status_code=400,
                detail=ApiError(message=f"SQL không hợp lệ: {exc}", error_code="SQL_ERROR").model_dump(),
            ) from exc

        columns = [item[0] for item in (db.cursor.description or [])]
        data = [dict(row) for row in rows]
        db.record_audit_log(
            actor_email=admin_email(admin),
            action="database.query.ran",
            target_type="database",
            target_id="sqlite",
            details={"query": limited_query[:1000], "rows": len(data)},
        )

    return ApiSuccess(data={"columns": columns, "rows": data, "query": limited_query})
