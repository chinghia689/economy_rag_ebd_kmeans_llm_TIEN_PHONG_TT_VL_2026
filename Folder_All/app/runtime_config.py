"""Runtime configuration backed by app_settings in the application database."""

from typing import Mapping

from app.logger import get_logger

logger = get_logger(__name__)


def get_runtime_setting(key: str, default: str = "") -> str:
    """Return a setting from DB first, then the provided default."""
    try:
        from chatbot.utils.base_db import UserDB

        with UserDB() as db:
            value = db.get_app_setting(key, default=None)
            if value is not None:
                return value
    except Exception as exc:
        logger.warning(f"Cannot read runtime setting {key} from DB: {exc}")

    return default


def get_runtime_settings(defaults: Mapping[str, str]) -> dict[str, str]:
    """Read several runtime settings with one DB connection when possible."""
    values: dict[str, str] = {}
    try:
        from chatbot.utils.base_db import UserDB

        with UserDB() as db:
            for key, default in defaults.items():
                value = db.get_app_setting(key, default=None)
                values[key] = value if value is not None else default
            return values
    except Exception as exc:
        logger.warning(f"Cannot read runtime settings from DB: {exc}")

    return dict(defaults)


def get_runtime_signature(keys: list[str]) -> tuple[tuple[str, str], ...]:
    """Build a value signature used to recreate cached clients when config changes."""
    values = get_runtime_settings({key: "" for key in keys})
    return tuple((key, values.get(key, "")) for key in keys)
