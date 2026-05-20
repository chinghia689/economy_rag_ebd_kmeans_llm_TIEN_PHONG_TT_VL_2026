"""Helpers chuẩn hoá text dùng chung cho query splitter / retriever."""

from __future__ import annotations

import re
import unicodedata


def clean_text(text: object) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", str(text or ""))).strip()


def dedupe_keep_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        v = clean_text(item)
        if v and v.lower() not in seen:
            seen.add(v.lower())
            out.append(v)
    return out


def is_bad_query_part(text: str) -> bool:
    v = clean_text(text)
    words = v.split()
    low = v.lower()
    if len(words) <= 2:
        return True
    if low in {"câu hỏi", "câu hỏi tuy nhiên", "tuy nhiên"}:
        return True
    if low.startswith("câu hỏi ") and len(words) <= 4:
        return True
    return False


def strip_question_label(question: str) -> str:
    v = clean_text(question)
    if ":" in v and re.match(r"^\s*câu\s*hỏi\b", v, flags=re.IGNORECASE):
        return clean_text(v.split(":", 1)[1])
    return re.sub(r"^\s*câu\s*hỏi\s*:\s*", "", v, flags=re.IGNORECASE).strip()


def fallback_query_parts(question: str, max_parts: int) -> list[str]:
    """Tạo query con dự phòng khi LLM split fail (tránh chỉ có 1 query vector)."""
    base = clean_text(re.sub(r"[?!.;:]+", " ", strip_question_label(question)))
    candidates: list[str] = []

    connector = re.compile(
        r"\s*(?:,|\bva\b|\bvà\b|\bhoac\b|\bhoặc\b|\bnhung\b|\bnhưng\b|"
        r"\bdong thoi\b|\bđồng thời\b|\bngoai ra\b|\bngoài ra\b)\s*",
        flags=re.IGNORECASE,
    )
    for piece in connector.split(base):
        piece = clean_text(piece)
        if len(piece.split()) >= 5:
            candidates.append(piece)

    stopwords = {
        "câu", "hỏi", "là", "gì", "nào", "bao", "nhiêu", "có", "không",
        "hãy", "cho", "biết", "về", "trong", "của", "ở", "đâu", "khi",
        "như", "thế", "được", "đã",
    }
    kw = [w for w in re.sub(r"[^\w\s]", " ", base.lower()).split() if w not in stopwords]
    if len(kw) >= 5:
        candidates.append(" ".join(kw))

    if base:
        candidates.append(f"Tìm đoạn văn chứa thông tin: {base}")

    return dedupe_keep_order([c for c in candidates if not is_bad_query_part(c)])[:max_parts]
