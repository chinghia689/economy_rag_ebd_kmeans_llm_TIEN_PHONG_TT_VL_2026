"""Read-only APIs for content displayed on public pages."""

from fastapi import APIRouter

from app.models.schemas import ApiSuccess
from app.public_content import PUBLIC_CONTENT_SETTING_DEFINITIONS, public_content_from_settings
from chatbot.utils.base_db import UserDB

router = APIRouter(prefix="/public", tags=["Public"])


@router.get("/content")
async def get_public_content():
    """Return non-secret privacy, terms, and support content without requiring login."""
    defaults = {
        definition["key"]: definition["default"]
        for definition in PUBLIC_CONTENT_SETTING_DEFINITIONS
    }
    with UserDB() as db:
        values = {
            key: db.get_app_setting(key, default) or ""
            for key, default in defaults.items()
        }
    return ApiSuccess(data=public_content_from_settings(values))
