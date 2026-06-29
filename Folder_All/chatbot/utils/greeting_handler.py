"""Fast, deterministic handling for greeting-only chat messages."""

from __future__ import annotations

import re
import unicodedata


GREETING_RESPONSE = (
    "Xin chào! Tôi có thể hỗ trợ bạn tra cứu thông tin kinh tế Việt Nam. "
    "Bạn muốn hỏi điều gì?"
)

_GREETING_PHRASES = {
    "alo",
    "ban khoe khong",
    "khoe khong",
    "chao",
    "chao ban",
    "chao bot",
    "chao chatbot",
    "chao buoi sang",
    "chao buoi trua",
    "chao buoi chieu",
    "chao buoi toi",
    "good afternoon",
    "good evening",
    "good morning",
    "hello there",
    "hello",
    "hello ban",
    "hello bot",
    "hello chatbot",
    "hey",
    "hi there",
    "hi",
    "hi ban",
    "hi bot",
    "hi chatbot",
    "xin chao",
    "xin chao ban",
    "xin chao bot",
    "how are you",
    "xin chao chatbot",
}

_POLITE_SUFFIXES = {"a", "nha", "nhe", "oi"}


def _normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", str(text or "").lower())
    ascii_text = "".join(
        char for char in decomposed if not unicodedata.combining(char)
    )
    return re.sub(r"[^a-z0-9]+", " ", ascii_text).strip()


def is_greeting_only(text: str) -> bool:
    """Return True only when the whole message is a supported greeting."""
    normalized = _normalize(text)
    if not normalized:
        return False

    words = normalized.split()
    while words and words[-1] in _POLITE_SUFFIXES:
        words.pop()

    return " ".join(words) in _GREETING_PHRASES


def get_greeting_response(text: str) -> str | None:
    return GREETING_RESPONSE if is_greeting_only(text) else None
