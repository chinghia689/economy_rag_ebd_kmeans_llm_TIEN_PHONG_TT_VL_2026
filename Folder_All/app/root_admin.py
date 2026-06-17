"""Root admin identity and password helpers."""

from __future__ import annotations

import base64
import hashlib
import secrets

ADMIN_LOGIN_ACCOUNT_KEY = "ADMIN_LOGIN_EMAIL"
ADMIN_LOGIN_PASSWORD_KEY = "ADMIN_LOGIN_PASSWORD"
DEFAULT_ADMIN_IDENTIFIER = "admin@local"
ADMIN_PASSWORD_HASH_SCHEME = "pbkdf2_sha256"
ADMIN_PASSWORD_ITERATIONS = 260_000


def normalize_admin_identifier(value: str | None) -> str:
    return (value or "").strip().lower()


def admin_identifier_aliases(value: str | None) -> set[str]:
    identifier = normalize_admin_identifier(value)
    if not identifier:
        return set()
    aliases = {identifier}
    if "@" not in identifier:
        aliases.add(f"{identifier}@local")
    elif identifier.endswith("@local"):
        aliases.add(identifier.split("@", 1)[0])
    return aliases


def canonical_admin_email(identifier: str | None) -> str:
    normalized = normalize_admin_identifier(identifier)
    if not normalized:
        return DEFAULT_ADMIN_IDENTIFIER
    return normalized if "@" in normalized else f"{normalized}@local"


def is_root_admin_email(email: str | None, root_identifier: str | None) -> bool:
    return canonical_admin_email(email) == canonical_admin_email(root_identifier)


def is_admin_password_hash(value: str | None) -> bool:
    return bool(value and value.startswith(f"{ADMIN_PASSWORD_HASH_SCHEME}$"))


def hash_admin_password(password: str) -> str:
    salt = secrets.token_urlsafe(18)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        ADMIN_PASSWORD_ITERATIONS,
    )
    encoded = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return f"{ADMIN_PASSWORD_HASH_SCHEME}${ADMIN_PASSWORD_ITERATIONS}${salt}${encoded}"


def verify_admin_password(password: str, stored_value: str | None) -> bool:
    stored = stored_value or ""
    if not is_admin_password_hash(stored):
        return secrets.compare_digest(password, stored)

    try:
        scheme, iterations_raw, salt, expected = stored.split("$", 3)
        iterations = int(iterations_raw)
    except (ValueError, TypeError):
        return False

    if scheme != ADMIN_PASSWORD_HASH_SCHEME or iterations <= 0 or not salt or not expected:
        return False

    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations,
    )
    actual = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return secrets.compare_digest(actual, expected)


def needs_admin_password_rehash(stored_value: str | None) -> bool:
    return bool(stored_value) and not is_admin_password_hash(stored_value)
