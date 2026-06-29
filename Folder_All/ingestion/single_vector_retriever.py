"""GT1 single-vector ERC: one query vector against K-Means document clusters."""

from __future__ import annotations

from typing import Any

import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

from ingestion.energy_base_distance import energy_base_distance


def _best_kmeans(vectors: np.ndarray) -> tuple[np.ndarray, int]:
    n = len(vectors)
    if n <= 2:
        return np.zeros(n, dtype=int), 1

    best_score = -float("inf")
    best_k = 2
    best_labels = None
    for k in range(2, min(10, n - 1) + 1):
        labels = KMeans(
            n_clusters=k,
            random_state=42,
            n_init="auto",
        ).fit_predict(vectors)
        score = silhouette_score(vectors, labels)
        if score > best_score:
            best_score = score
            best_k = k
            best_labels = labels

    print(f"   -> K toi uu = {best_k} (Silhouette = {best_score:.4f})")
    return best_labels, best_k


class SingleVectorERC:
    """
    Use one embedded question as distribution X and each document cluster as Y.

    The candidates are the top-k documents returned for the original question.
    The selected cluster is the one with the smallest Energy Distance to X.
    """

    def __init__(
        self,
        vector_store: Any,
        embeddings: Any,
        k_retrieve: int = 40,
        n_top_clusters: int = 1,
    ) -> None:
        self.retriever = vector_store.as_retriever(
            search_kwargs={"k": k_retrieve}
        )
        self.embeddings = embeddings
        self.n_top_clusters = n_top_clusters

        self.last_query_parts: list[str] = []
        self.last_retrieval_debug: list[dict[str, Any]] = []
        self.last_algorithm = "GT1_single_vector_erc"

    def retrieve(self, query: str) -> list[Any]:
        query = (query or "").strip()
        self.last_query_parts = [query] if query else []
        self.last_retrieval_debug = []
        if not query:
            return []

        docs = self.retriever.invoke(query)
        if not docs:
            print("   -> Khong tim thay docs.")
            return []

        doc_vecs = np.asarray(
            self.embeddings.embed_documents(
                [doc.page_content for doc in docs]
            )
        )
        query_vec = np.asarray(
            self.embeddings.embed_query(query)
        ).reshape(1, -1)
        print(f"   -> 1 query vector | {len(docs)} candidate docs")

        labels, k = _best_kmeans(doc_vecs)
        clusters = [
            (
                cluster_id,
                energy_base_distance(
                    query_vec,
                    doc_vecs[labels == cluster_id],
                ),
            )
            for cluster_id in range(k)
            if (labels == cluster_id).any()
        ]
        clusters.sort(key=lambda item: item[1])

        selected = clusters[: self.n_top_clusters]
        for cluster_id, distance in selected:
            print(
                f"   -> Cum {cluster_id} - "
                f"Energy Distance = {distance:.4f}"
            )

        final_docs = [
            docs[index]
            for cluster_id, _ in selected
            for index in np.where(labels == cluster_id)[0]
        ]
        print(f"   -> Tra ve {len(final_docs)} docs")
        return final_docs
