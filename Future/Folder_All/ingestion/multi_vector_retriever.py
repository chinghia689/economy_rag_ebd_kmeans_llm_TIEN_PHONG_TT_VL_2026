"""
SplitQueryEnergyRetriever — Energy Distance giữa phân phối query và cluster docs.

X = [vector(câu gốc), vector(query con 1), ..., vector(query con N)]
Y = vectors của docs trong từng cluster K-Means
Chọn cluster có Energy Distance nhỏ nhất.
"""

from __future__ import annotations

import hashlib
import os
from typing import Any

import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.metrics.pairwise import cosine_similarity

from ingestion._text_utils import clean_text
from ingestion.energy_base_distance import energy_base_distance
from ingestion.query_splitter import LLMQuerySplitter


class SplitQueryEnergyRetriever:
    def __init__(
        self,
        vector_store: Any,
        embeddings: Any,
        query_splitter: LLMQuerySplitter,
        k_retrieve: int = 40,
        n_top_clusters: int = 1,
        max_final_docs: int = 0,
    ) -> None:
        self.retriever = vector_store.as_retriever(search_kwargs={"k": k_retrieve})
        self.embeddings = embeddings
        self.n_top_clusters = n_top_clusters
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
        print(f"\n🔎 [LLM Query Split] {len(query_parts)} query parts: {query_parts}")
        return self._run_energy_retrieval(query_parts)

    def retrieve_from_parts(self, parts: list[str]) -> list[Any]:
        """Dùng trực tiếp list parts, bỏ qua LLM split."""
        query_parts = [clean_text(p) for p in parts if clean_text(p)]
        if not query_parts:
            return []
        print(f"\n🔎 [Manual Parts] {len(query_parts)} query parts: {query_parts}")
        return self._run_energy_retrieval(query_parts)

    def _run_energy_retrieval(self, query_parts: list[str]) -> list[Any]:
        self.last_query_parts = list(query_parts)
        self.last_retrieval_debug = []

        candidates, seen, debug = self._collect_candidates(query_parts)
        if not candidates:
            print("   -> ⚠️ Không tìm thấy tài liệu thô nào.")
            self.last_retrieval_debug = self._compact_debug(debug)
            return []

        doc_vecs = np.array(self.embeddings.embed_documents([d.page_content for d in candidates]))
        query_vecs = np.array([self.embeddings.embed_query(p) for p in query_parts])

        self._annotate_similarities(debug, candidates, doc_vecs, query_vecs)
        print(f"   -> Max Cosine Similarity: {np.max(cosine_similarity(query_vecs, doc_vecs)):.4f}")
        print(f"   -> 📋 {len(query_vecs)} query vectors và {len(doc_vecs)} doc vectors")

        labels, k = self._best_kmeans(doc_vecs)
        selected = self._select_clusters(query_vecs, doc_vecs, labels, k)

        final_docs, picked = self._gather_docs(candidates, labels, selected)
        self._annotate_clusters(debug, candidates, labels, picked)
        self.last_retrieval_debug = self._compact_debug(debug)

        print(f"   -> ✅ Truy xuất {len(final_docs)} documents từ phân phối query")
        return final_docs

    def _collect_candidates(self, query_parts: list[str]) -> tuple[list, set, list]:
        candidates: list[Any] = []
        seen: set[str] = set()
        debug: list[dict[str, Any]] = []

        for part_idx, part in enumerate(query_parts, 1):
            for rank, doc in enumerate(self.retriever.invoke(part), 1):
                key = self._doc_key(doc)
                meta = getattr(doc, "metadata", {}) or {}
                debug.append({
                    "query_part_index": part_idx,
                    "query_part": part,
                    "rank": rank,
                    "source": meta.get("source", ""),
                    "filename": meta.get("filename", ""),
                    "page": meta.get("page", ""),
                    "content_preview": clean_text(getattr(doc, "page_content", ""))[: self.debug_preview_chars],
                    "_doc_key": key,
                })
                if key not in seen:
                    seen.add(key)
                    candidates.append(doc)
        return candidates, seen, debug

    @staticmethod
    def _best_kmeans(vectors: np.ndarray) -> tuple[np.ndarray, int]:
        n = len(vectors)
        if n <= 2:
            print(f"   -> ⚠️ Số docs quá ít ({n}), gom thành 1 cụm.")
            return np.zeros(n, dtype=int), 1

        best_score, best_k, best_labels = -float("inf"), 2, None
        for k in range(2, min(10, n - 1) + 1):
            labels = KMeans(n_clusters=k, random_state=42, n_init="auto").fit_predict(vectors)
            score = silhouette_score(vectors, labels)
            if score > best_score:
                best_score, best_k, best_labels = score, k, labels
        print(f"   -> 🤖 K tối ưu = {best_k} (Silhouette = {best_score:.4f})")
        return best_labels, best_k

    def _select_clusters(self, query_vecs, doc_vecs, labels, k) -> list[tuple[int, float]]:
        clusters = [
            (cid, energy_base_distance(query_vecs, doc_vecs[labels == cid]))
            for cid in range(k)
            if (labels == cid).any()
        ]
        clusters.sort(key=lambda x: x[1])
        selected = clusters[: self.n_top_clusters]
        for i, (cid, ed) in enumerate(selected):
            print(f"   -> {'🏆' if i == 0 else '📌'} Cụm {cid} - Energy Distance = {ed:.4f}")
        return selected

    def _gather_docs(self, candidates, labels, selected) -> tuple[list, set[int]]:
        final_docs, picked = [], set()
        for cid, _ in selected:
            for idx in np.where(labels == cid)[0]:
                if idx in picked:
                    continue
                picked.add(idx)
                final_docs.append(candidates[idx])
                if self.max_final_docs and len(final_docs) >= self.max_final_docs:
                    return final_docs, picked
        return final_docs, picked

    def _annotate_similarities(self, debug, candidates, doc_vecs, query_vecs) -> None:
        sims = cosine_similarity(query_vecs, doc_vecs)
        idx_by_key = {self._doc_key(d): i for i, d in enumerate(candidates)}
        for entry in debug:
            di = idx_by_key.get(entry["_doc_key"])
            qi = entry["query_part_index"] - 1
            if di is not None and 0 <= qi < len(query_vecs):
                sim = float(sims[qi, di])
                entry["cosine_similarity"] = sim
                entry["distance"] = float(1.0 - sim)

    def _annotate_clusters(self, debug, candidates, labels, picked) -> None:
        idx_by_key = {self._doc_key(d): i for i, d in enumerate(candidates)}
        for entry in debug:
            di = idx_by_key.get(entry["_doc_key"])
            if di is not None:
                entry["cluster"] = int(labels[di])
                entry["selected_by_energy_cluster"] = di in picked

    def _compact_debug(self, entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
        kept = [
            e for e in entries
            if e.get("rank", 999999) <= self.debug_top_per_query
            or e.get("selected_by_energy_cluster")
        ]
        kept.sort(key=lambda e: (e.get("query_part_index", 0), e.get("rank", 0)))
        return [{k: v for k, v in e.items() if k != "_doc_key"} for e in kept[: self.debug_max_entries]]

    @staticmethod
    def _doc_key(doc: Any) -> str:
        meta = getattr(doc, "metadata", {}) or {}
        content = clean_text(getattr(doc, "page_content", ""))
        h = hashlib.md5(content.encode("utf-8")).hexdigest()
        return f"{clean_text(meta.get('source',''))}:{clean_text(meta.get('filename',''))}:{clean_text(meta.get('page',''))}:{h}"
