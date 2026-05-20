"""GT1 — Multi-vector ERC: phân phối query vectors vs cluster docs (K-Means)."""

from __future__ import annotations

import hashlib
from typing import Any

import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

from .energy_base_distance import energy_base_distance


def _doc_key(doc: Any) -> str:
    meta = getattr(doc, "metadata", {}) or {}
    h = hashlib.md5(getattr(doc, "page_content", "").encode()).hexdigest()
    return f"{meta.get('source', '')}:{meta.get('page', '')}:{h}"


def _best_kmeans(vectors: np.ndarray) -> tuple[np.ndarray, int]:
    n = len(vectors)
    if n <= 2:
        return np.zeros(n, dtype=int), 1
    best_score, best_k, best_labels = -1.0, 2, None
    for k in range(2, min(10, n - 1) + 1):
        labels = KMeans(n_clusters=k, random_state=42, n_init="auto").fit_predict(vectors)
        score = silhouette_score(vectors, labels)
        if score > best_score:
            best_score, best_k, best_labels = score, k, labels
    print(f"   -> K tối ưu = {best_k} (Silhouette = {best_score:.4f})")
    return best_labels, best_k


class MultiVectorERC:
    """
    X = [embed(câu hỏi gốc), embed(sub_1), ..., embed(sub_N)]
    Y = doc vectors trong từng cụm K-Means.
    Chọn cụm có Energy Distance nhỏ nhất.
    """

    def __init__(self, vector_store: Any, embeddings: Any, k_retrieve: int = 40, n_top_clusters: int = 1):
        self.retriever = vector_store.as_retriever(search_kwargs={"k": k_retrieve})
        self.embeddings = embeddings
        self.n_top_clusters = n_top_clusters

    def retrieve(self, query_parts: list[str]) -> list[Any]:
        if not query_parts:
            return []

        seen, candidates = set(), []
        for part in query_parts:
            for doc in self.retriever.invoke(part):
                key = _doc_key(doc)
                if key not in seen:
                    seen.add(key)
                    candidates.append(doc)

        if not candidates:
            print("   -> ⚠️ Không tìm thấy docs.")
            return []

        doc_vecs = np.array(self.embeddings.embed_documents([d.page_content for d in candidates]))
        query_vecs = np.array([self.embeddings.embed_query(p) for p in query_parts])
        print(f"   -> {len(query_vecs)} query vecs | {len(candidates)} candidate docs")

        labels, k = _best_kmeans(doc_vecs)
        clusters = [
            (cid, energy_base_distance(query_vecs, doc_vecs[labels == cid]))
            for cid in range(k)
            if (labels == cid).any()
        ]
        clusters.sort(key=lambda x: x[1])

        selected = clusters[: self.n_top_clusters]
        for i, (cid, ed) in enumerate(selected):
            print(f"   -> {'🏆' if i == 0 else '📌'} Cụm {cid} — ED = {ed:.4f}")

        final = [candidates[i] for cid, _ in selected for i in np.where(labels == cid)[0]]
        print(f"   -> ✅ Trả về {len(final)} docs")
        return final
