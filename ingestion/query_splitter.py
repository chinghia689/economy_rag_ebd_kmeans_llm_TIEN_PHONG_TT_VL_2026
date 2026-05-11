"""
LLM query splitting cho pipeline retrieval chính.

Luồng dùng trong chatbot:
    question gốc -> LLM tách query parts -> lấy candidate docs từ từng part
    -> Energy Distance giữa phân phối query và từng cụm docs
    -> DocumentGrader lọc bằng question gốc -> AnswerGenerator sinh answer.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import unicodedata
from typing import Any

import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.metrics.pairwise import cosine_similarity

from ingestion.energy_base_distance import energy_base_distance


def _clean_text(text: object) -> str:
    normalized = unicodedata.normalize("NFC", str(text or ""))
    return re.sub(r"\s+", " ", normalized).strip()


def _strip_question_label(question: str) -> str:
    value = _clean_text(question)
    if ":" in value and re.match(r"^\s*câu\s*hỏi\b", value, flags=re.IGNORECASE):
        return _clean_text(value.split(":", 1)[1])
    return re.sub(r"^\s*câu\s*hỏi\s*:\s*", "", value, flags=re.IGNORECASE).strip()


def _is_bad_query_part(text: str) -> bool:
    value = _clean_text(text)
    words = value.split()
    lowered = value.lower()
    if len(words) <= 2:
        return True
    if lowered in {"câu hỏi", "câu hỏi tuy nhiên", "tuy nhiên"}:
        return True
    if lowered.startswith("câu hỏi ") and len(words) <= 4:
        return True
    return False


def _dedupe_keep_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    results: list[str] = []

    for item in items:
        value = _clean_text(item)
        key = value.lower()
        if not value or key in seen:
            continue
        seen.add(key)
        results.append(value)

    return results


def _fallback_query_parts(question: str, max_parts: int) -> list[str]:
    """
    Tạo query con dự phòng khi LLM không tách được.

    Mục tiêu là tránh trường hợp chỉ còn 1 query vector, vì khi đó phân phối
    query bị suy biến. Fallback này không thay câu hỏi gốc ở bước grade/generate,
    chỉ tạo thêm biến thể truy vấn cho retrieval.
    """

    base = _strip_question_label(question)
    base = _clean_text(re.sub(r"[?!.;:]+", " ", base))
    candidates: list[str] = []

    connector_pattern = re.compile(
        r"\s*(?:,|\bva\b|\bvà\b|\bhoac\b|\bhoặc\b|\bnhung\b|\bnhưng\b|"
        r"\bdong thoi\b|\bđồng thời\b|\bngoai ra\b|\bngoài ra\b)\s*",
        flags=re.IGNORECASE,
    )
    for piece in connector_pattern.split(base):
        piece = _clean_text(piece)
        if len(piece.split()) >= 5:
            candidates.append(piece)

    stopwords = {
        "câu", "hỏi", "là", "gì", "nào", "bao", "nhiêu", "có", "không",
        "hãy", "cho", "biết", "về", "trong", "của", "ở", "đâu", "khi",
        "như", "thế", "nào", "được", "đã",
    }
    keyword_words = [
        word
        for word in re.sub(r"[^\w\s]", " ", base.lower()).split()
        if word not in stopwords
    ]
    keyword_query = " ".join(keyword_words)
    if len(keyword_words) >= 5:
        candidates.append(keyword_query)

    if base:
        candidates.append(f"Tìm đoạn văn chứa thông tin: {base}")

    candidates = [item for item in candidates if not _is_bad_query_part(item)]
    return _dedupe_keep_order(candidates)[:max_parts]


class LLMQuerySplitter:
    """
    Dùng LLM để tách câu hỏi dài/phức tạp thành nhiều query nhỏ hơn.

    Query con chỉ phục vụ retrieval. Câu hỏi gốc vẫn được dùng ở bước
    lọc context và sinh câu trả lời để không mất ý định ban đầu.
    """

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
        min_sub_parts = self.min_query_vectors - 1 if include_original else self.min_query_vectors
        self.max_parts = max(1, max_parts, min_sub_parts)
        self._cache: dict[str, list[str]] = {}

    def split(self, question: str) -> list[str]:
        question = _clean_text(question)
        if not question:
            return []

        if question in self._cache:
            return list(self._cache[question])

        try:
            response = self.llm.invoke(
                self.PROMPT_TEMPLATE.format(
                    question=question,
                    max_parts=self.max_parts,
                )
            )
            content = getattr(response, "content", response)
            parts = self._parse_response(str(content))
        except Exception as exc:
            print(f"⚠️ LLM query split lỗi, fallback về query gốc: {exc}")
            parts = []

        parts = [
            part
            for part in _dedupe_keep_order(parts[: self.max_parts])
            if not _is_bad_query_part(part)
        ]
        if len(parts) < self.max_parts:
            parts = _dedupe_keep_order(
                [*parts, *_fallback_query_parts(question, self.max_parts)]
            )

        if self.include_original:
            parts = [question, *parts]

        parts = _dedupe_keep_order(parts) or [question]
        if len(parts) < self.min_query_vectors:
            parts = _dedupe_keep_order(
                [*parts, f"Tìm thông tin liên quan đến {question}"]
            )

        max_total_parts = self.max_parts + (1 if self.include_original else 0)
        parts = parts[:max_total_parts]
        self._cache[question] = parts
        return list(parts)

    def _parse_response(self, text: str) -> list[str]:
        json_match = re.search(r"\[[\s\S]*\]", text)
        if json_match:
            try:
                parsed = json.loads(json_match.group(0))
                if isinstance(parsed, list):
                    return _dedupe_keep_order([str(item) for item in parsed])
            except Exception:
                pass

        lines = re.split(r"(?:\n|;)+", text)
        cleaned: list[str] = []
        for line in lines:
            line = re.sub(r"^\s*[-*\d.)]+\s*", "", line)
            line = _clean_text(line.strip("\"' "))
            if line:
                cleaned.append(line)
        return _dedupe_keep_order(cleaned)


class SplitQueryEnergyRetriever:
    """
    Dùng toàn bộ query parts như một phân phối query để tính Energy Distance.

    Không gọi EnergyRetriever.retrieve() riêng cho từng query con, vì như vậy
    mỗi lần Energy Distance chỉ thấy một query vector. Ở đây:
        X = tập vector của [câu hỏi gốc, câu hỏi con 1, câu hỏi con 2, ...]
        Y = tập vector của documents trong từng cluster
    rồi tính energy_base_distance(X, Y).
    """

    def __init__(
        self,
        energy_retriever: Any,
        query_splitter: LLMQuerySplitter,
        max_final_docs: int = 0,
    ) -> None:
        self.energy_retriever = energy_retriever
        self.query_splitter = query_splitter
        self.max_final_docs = max_final_docs if max_final_docs > 0 else None
        self.last_query_parts: list[str] = []
        self.last_retrieval_debug: list[dict[str, Any]] = []
        self.last_algorithm = "llm_query_split_energy_kmeans"
        self.debug_top_per_query = int(os.getenv("QUERY_SPLIT_DEBUG_TOP_PER_QUERY", "5"))
        self.debug_max_entries = int(os.getenv("QUERY_SPLIT_DEBUG_MAX_ENTRIES", "40"))
        self.debug_preview_chars = int(os.getenv("QUERY_SPLIT_DEBUG_PREVIEW_CHARS", "120"))

    def retrieve(self, query: str) -> list[Any]:
        query_parts = self.query_splitter.split(query)
        self.last_query_parts = list(query_parts)
        self.last_retrieval_debug = []
        print(f"\n🔎 [LLM Query Split] {len(query_parts)} query parts: {query_parts}")

        candidate_docs: list[Any] = []
        seen_docs: set[str] = set()
        debug_entries: list[dict[str, Any]] = []
        for part_index, part in enumerate(query_parts, start=1):
            docs = self.energy_retriever.retriever.invoke(part)
            for rank, doc in enumerate(docs, start=1):
                key = self._doc_key(doc)
                metadata = getattr(doc, "metadata", {}) or {}
                debug_entries.append(
                    {
                        "query_part_index": part_index,
                        "query_part": part,
                        "rank": rank,
                        "source": metadata.get("source", ""),
                        "filename": metadata.get("filename", ""),
                        "page": metadata.get("page", ""),
                        "content_preview": _clean_text(getattr(doc, "page_content", ""))[: self.debug_preview_chars],
                        "_doc_key": key,
                    }
                )
                if key in seen_docs:
                    continue
                seen_docs.add(key)
                candidate_docs.append(doc)

        if not candidate_docs:
            print("   -> ⚠️ Không tìm thấy tài liệu thô nào.")
            self.last_retrieval_debug = self._compact_debug_entries(debug_entries)
            return []

        context = [doc.page_content for doc in candidate_docs]
        doc_vectors = np.array(self.energy_retriever.embeddings.embed_documents(context))
        query_vectors = np.array(
            [self.energy_retriever.embeddings.embed_query(part) for part in query_parts]
        )

        sims = cosine_similarity(query_vectors, doc_vectors)
        doc_index_by_key = {
            self._doc_key(doc): index
            for index, doc in enumerate(candidate_docs)
        }
        for entry in debug_entries:
            doc_index = doc_index_by_key.get(entry["_doc_key"])
            query_index = entry["query_part_index"] - 1
            if doc_index is not None and 0 <= query_index < len(query_vectors):
                similarity = float(sims[query_index, doc_index])
                entry["cosine_similarity"] = similarity
                entry["distance"] = float(1.0 - similarity)

        print(f"   -> Max Cosine Similarity: {np.max(sims):.4f}")

        n_samples = len(doc_vectors)
        print(
            f"   -> 📋 Đưa {len(query_vectors)} query vectors và "
            f"{n_samples} doc vectors vào Energy Distance"
        )

        max_possible_k = min(10, n_samples - 1)
        if n_samples > 2:
            best_score = -1.0
            best_k = 2
            best_labels = None

            for k in range(2, max_possible_k + 1):
                kmeans_temp = KMeans(n_clusters=k, random_state=42, n_init="auto")
                labels_temp = kmeans_temp.fit_predict(doc_vectors)
                score = silhouette_score(doc_vectors, labels_temp)
                if score > best_score:
                    best_score = score
                    best_k = k
                    best_labels = labels_temp

            labels = best_labels
            actual_k = best_k
            print(
                f"   -> 🤖 Tự động chọn K tối ưu = {best_k} "
                f"(Silhouette Score cao nhất: {best_score:.4f})"
            )
        else:
            labels = np.zeros(n_samples, dtype=int)
            actual_k = 1
            print(f"   -> ⚠️ Số lượng docs quá ít ({n_samples}), tự động gom thành 1 cụm.")

        cluster_energies = []
        for i in range(actual_k):
            cluster_mask = labels == i
            if not np.any(cluster_mask):
                continue

            cluster_vectors = doc_vectors[cluster_mask]
            energy = energy_base_distance(query_vectors, cluster_vectors)
            cluster_energies.append((i, energy))

        cluster_energies.sort(key=lambda item: item[1])
        n_select = min(self.energy_retriever.n_top_clusters, len(cluster_energies))
        selected_clusters = cluster_energies[:n_select]

        for idx, (cluster_id, energy) in enumerate(selected_clusters):
            icon = "🏆" if idx == 0 else "📌"
            print(f"   -> {icon} Cụm {cluster_id} - Energy Distance = {energy:.4f}")

        final_docs = []
        seen_indices: set[int] = set()
        for cluster_id, _ in selected_clusters:
            win_mask = labels == cluster_id
            win_local_indices = np.where(win_mask)[0]
            for local_index in win_local_indices:
                if local_index in seen_indices:
                    continue
                seen_indices.add(local_index)
                final_docs.append(candidate_docs[local_index])
                if self.max_final_docs and len(final_docs) >= self.max_final_docs:
                    break
            if self.max_final_docs and len(final_docs) >= self.max_final_docs:
                break

        for entry in debug_entries:
            doc_index = doc_index_by_key.get(entry["_doc_key"])
            if doc_index is not None:
                entry["cluster"] = int(labels[doc_index])
                entry["selected_by_energy_cluster"] = doc_index in seen_indices

        self.last_retrieval_debug = self._compact_debug_entries(debug_entries)

        print(f"   -> ✅ Truy xuất {len(final_docs)} documents từ phân phối query")
        return final_docs

    def _compact_debug_entries(self, entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
        kept = [
            entry
            for entry in entries
            if entry.get("rank", 999999) <= self.debug_top_per_query
            or entry.get("selected_by_energy_cluster")
        ]
        kept.sort(key=lambda entry: (entry.get("query_part_index", 0), entry.get("rank", 0)))
        cleaned = []
        for entry in kept[: self.debug_max_entries]:
            cleaned.append(
                {
                    key: value
                    for key, value in entry.items()
                    if key != "_doc_key"
                }
            )
        return cleaned

    def _doc_key(self, doc: Any) -> str:
        metadata = getattr(doc, "metadata", {}) or {}
        source = _clean_text(metadata.get("source", ""))
        filename = _clean_text(metadata.get("filename", ""))
        page = _clean_text(metadata.get("page", ""))
        content = _clean_text(getattr(doc, "page_content", ""))
        content_hash = hashlib.md5(content.encode("utf-8")).hexdigest()
        return f"{source}:{filename}:{page}:{content_hash}"
