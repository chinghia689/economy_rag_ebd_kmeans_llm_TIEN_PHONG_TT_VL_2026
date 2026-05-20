"""
GT3 — LLM Fixed-N Splitter.

LLM tách câu hỏi thành ĐÚNG N sub-queries (N=1..4 do người dùng chỉ định).
Khác GT1 (auto): N cố định, không phụ thuộc độ phức tạp câu hỏi.
"""

from __future__ import annotations

import json
import re
import unicodedata
from typing import Any


def _clean(text: object) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", str(text or ""))).strip()


def _dedupe(items: list[str]) -> list[str]:
    seen, out = set(), []
    for item in items:
        v = _clean(item)
        if v and v.lower() not in seen:
            seen.add(v.lower())
            out.append(v)
    return out


def _is_valid(text: str) -> bool:
    v = _clean(text)
    return len(v.split()) > 2 and v.lower() not in {"câu hỏi", "tuy nhiên"}


def _strip_question_label(question: str) -> str:
    v = _clean(question)
    if ":" in v and re.match(r"^\s*câu\s*hỏi\b", v, flags=re.IGNORECASE):
        return _clean(v.split(":", 1)[1])
    return re.sub(r"^\s*câu\s*hỏi\s*:\s*", "", v, flags=re.IGNORECASE).strip()


def _fallback_query_parts(question: str, max_parts: int) -> list[str]:
    """Tạo query con dự phòng khi LLM split fail (tránh chỉ có 1 query vector)."""
    base = _clean(re.sub(r"[?!.;:]+", " ", _strip_question_label(question)))
    candidates: list[str] = []

    connector = re.compile(
        r"\s*(?:,|\bva\b|\bvà\b|\bhoac\b|\bhoặc\b|\bnhung\b|\bnhưng\b|"
        r"\bdong thoi\b|\bđồng thời\b|\bngoai ra\b|\bngoài ra\b)\s*",
        flags=re.IGNORECASE,
    )
    for piece in connector.split(base):
        piece = _clean(piece)
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

    return _dedupe([c for c in candidates if _is_valid(c)])[:max_parts]


def _parse_json_array(text: str) -> list[str]:
    match = re.search(r"\[[\s\S]*\]", text)
    if match:
        try:
            parsed = json.loads(match.group(0))
            if isinstance(parsed, list):
                return [str(i) for i in parsed]
        except json.JSONDecodeError:
            pass
    lines = (re.sub(r"^\s*[-*\d.)]+\s*", "", l).strip("\"' ") for l in text.splitlines())
    return [_clean(l) for l in lines if _clean(l)]


class LLMFixedNSplitter:
    """LLM tách câu hỏi thành ĐÚNG N sub-queries (N=1..4)."""

    PROMPT = """Bạn hãy tách câu hỏi sau thành các truy vấn con để tìm đúng đoạn văn trong vector database.
Yêu cầu:
- Giữ nguyên ý nghĩa gốc, không tự thêm thông tin.
- Ưu tiên giữ nguyên các cụm từ khóa quan trọng, thực thể, thời gian, đơn vị, quan hệ trong câu hỏi.
- Với câu hỏi dạng điền khuyết như "bao nhiêu", "nào", "ở đâu", hãy giữ các từ khóa xung quanh chỗ cần tìm; không suy đoán đáp án.
- Mỗi truy vấn con phải đủ nghĩa khi đứng riêng và không được quá chung.
- Không tạo truy vấn kiểu "Câu hỏi", "Tuy nhiên", hoặc mảnh câu không có từ khóa chính.
- Nếu câu hỏi đã đơn giản, hãy diễn đạt lại thành một truy vấn tìm kiếm ngắn giàu từ khóa.
- Tối đa {num_queries} câu.
- Chỉ trả về JSON array string, ví dụ: ["câu hỏi con 1", "câu hỏi con 2"].

Câu hỏi: {question}
"""

    def __init__(self, llm: Any, num_queries: int = 2) -> None:
        if not 1 <= num_queries <= 4:
            raise ValueError("num_queries phải từ 1 đến 4")
        self.llm = llm
        self.num_queries = num_queries
        self._cache: dict[str, list[str]] = {}

    def split(self, question: str) -> list[str]:
        """Trả về [câu gốc, sub_1, ..., sub_N] — tổng N+1 vectors."""
        question = _clean(question)
        if not question:
            return []
        key = f"{self.num_queries}:{question}"
        if key in self._cache:
            return list(self._cache[key])

        try:
            response = self.llm.invoke(
                self.PROMPT.format(question=question, num_queries=self.num_queries)
            )
            content = str(getattr(response, "content", response))
            parts = _dedupe([p for p in _parse_json_array(content) if _is_valid(p)])
        except Exception as exc:
            print(f"⚠️ LLM split failed: {exc}")
            parts = []

        parts = parts[: self.num_queries]
        if len(parts) < self.num_queries:
            parts = _dedupe([*parts, *_fallback_query_parts(question, self.num_queries)])
            parts = parts[: self.num_queries]
        while len(parts) < self.num_queries:
            parts.append(f"Thông tin về: {question} (góc {len(parts) + 1})")

        all_parts = _dedupe([question, *parts])[: self.num_queries + 1]
        self._cache[key] = all_parts
        return list(all_parts)
