"""
LLMQuerySplitter — tách câu hỏi thành nhiều query con để retrieval.

Chỉ phục vụ retrieval; câu hỏi gốc vẫn dùng ở grade + generate.
"""

from __future__ import annotations

import json
import re
from typing import Any

from ingestion._text_utils import (
    clean_text,
    dedupe_keep_order,
    fallback_query_parts,
    is_bad_query_part,
)


class LLMQuerySplitter:
    PROMPT_TEMPLATE = """Bạn hãy tách câu hỏi sau thành các truy vấn con để tìm đúng đoạn văn trong vector database.
Yêu cầu:
- Giữ nguyên ý nghĩa gốc, không tự thêm thông tin.
- Ưu tiên giữ nguyên các cụm từ khóa quan trọng, thực thể, thời gian, đơn vị, quan hệ trong câu hỏi.
- Với câu hỏi dạng điền khuyết như "bao nhiêu", "nào", "ở đâu", hãy giữ các từ khóa xung quanh chỗ cần tìm; không suy đoán đáp án.
- Mỗi truy vấn con phải đủ nghĩa khi đứng riêng và không được quá chung.
- Không tạo truy vấn kiểu "Câu hỏi", "Tuy nhiên", hoặc mảnh câu không có từ khóa chính.
- Nếu câu hỏi đã đơn giản, hãy diễn đạt lại thành một truy vấn tìm kiếm ngắn giàu từ khóa.
- Tối đa {max_parts} câu.
- Chỉ trả về JSON array string, ví dụ: ["câu hỏi con 1", "câu hỏi con 2"].

Câu hỏi: {question}
"""

    def __init__(
        self,
        llm: Any,
        max_parts: int = 4,
        include_original: bool = True,
        min_query_vectors: int = 2,
    ) -> None:
        self.llm = llm
        self.include_original = include_original
        self.min_query_vectors = max(1, min_query_vectors)
        min_sub = self.min_query_vectors - 1 if include_original else self.min_query_vectors
        self.max_parts = max(1, max_parts, min_sub)
        self._cache: dict[str, list[str]] = {}

    def split(self, question: str) -> list[str]:
        question = clean_text(question)
        if not question:
            return []
        if question in self._cache:
            return list(self._cache[question])

        try:
            response = self.llm.invoke(
                self.PROMPT_TEMPLATE.format(question=question, max_parts=self.max_parts)
            )
            content = getattr(response, "content", response)
            parts = self._parse_response(str(content))
        except Exception as exc:
            print(f"⚠️ LLM query split lỗi, fallback về query gốc: {exc}")
            parts = []

        parts = [p for p in dedupe_keep_order(parts[: self.max_parts]) if not is_bad_query_part(p)]
        if len(parts) < self.max_parts:
            parts = dedupe_keep_order([*parts, *fallback_query_parts(question, self.max_parts)])

        if self.include_original:
            parts = [question, *parts]

        parts = dedupe_keep_order(parts) or [question]
        if len(parts) < self.min_query_vectors:
            parts = dedupe_keep_order([*parts, f"Tìm thông tin liên quan đến {question}"])

        total_max = self.max_parts + (1 if self.include_original else 0)
        parts = parts[:total_max]
        self._cache[question] = parts
        return list(parts)

    def _parse_response(self, text: str) -> list[str]:
        match = re.search(r"\[[\s\S]*\]", text)
        if match:
            try:
                parsed = json.loads(match.group(0))
                if isinstance(parsed, list):
                    return dedupe_keep_order([str(i) for i in parsed])
            except Exception:
                pass

        lines = (re.sub(r"^\s*[-*\d.)]+\s*", "", l).strip("\"' ") for l in re.split(r"(?:\n|;)+", text))
        return dedupe_keep_order([clean_text(l) for l in lines if clean_text(l)])
