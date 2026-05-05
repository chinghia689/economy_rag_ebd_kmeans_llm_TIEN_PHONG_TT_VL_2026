"""
Đánh giá retrieval BM25 + E5 + Energy KMeans trên MS MARCO.

Dùng in-memory msmarco_embeddings.npy (42,791 vector) + doc_ids.json
và chạy thuật toán của bạn nguyên bản qua Mock VectorStore.
"""

import os
import sys
import json
import numpy as np
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import ir_datasets
from sklearn.metrics.pairwise import cosine_similarity
from langchain_core.documents import Document

from scoring_ms.evaluation_metric.ndcg_ms import ndcg_excel
from scoring_ms.evaluation_metric.mrr_ms import mrr_excel
from ingestion.energy_kmeans import EnergyRetriever


class NumpyRetriever:
    """Mock Retriever giống hệt Chroma cho MS MARCO"""
    def __init__(self, doc_ids, all_embeddings, docs_store, embeddings_model, k_retrieve):
        self.doc_ids = doc_ids
        self.all_embeddings = all_embeddings
        self.docs_store = docs_store
        self.embeddings_model = embeddings_model
        self.k = k_retrieve

    def invoke(self, query):
        # 1. Cosine similarity
        query_vec = np.array(self.embeddings_model.embed_query(query)).reshape(1, -1)
        sims = cosine_similarity(query_vec, self.all_embeddings)[0]
        top_indices = np.argsort(sims)[::-1][:self.k]

        # 2. Tạo danh sách Document
        docs = []
        for idx in top_indices:
            doc_id = self.doc_ids[idx]
            try:
                text = self.docs_store.get(doc_id).text
            except:
                text = ""
            docs.append(Document(page_content=text, metadata={"id": doc_id}))
        return docs

class NumpyVectorStore:
    """Mock VectorStore để tương thích ngầm với thuật toán EnergyRetriever của bạn"""
    def __init__(self, doc_ids, all_embeddings, docs_store, embeddings_model):
        self.doc_ids = doc_ids
        self.all_embeddings = all_embeddings
        self.docs_store = docs_store
        self.embeddings_model = embeddings_model

    def as_retriever(self, search_kwargs):
        k_retrieve = search_kwargs.get("k", 40)
        return NumpyRetriever(self.doc_ids, self.all_embeddings, self.docs_store, self.embeddings_model, k_retrieve)


def load_questions(excel_path, max_questions=None):
    df = pd.read_excel(excel_path)
    if max_questions:
        df = df.head(max_questions)
    results = []
    for _, row in df.iterrows():
        results.append({
            "query_id": str(row["query_id"]).strip() if "query_id" in row else "",
            "question": str(row["question"]).strip(),
            "qrels": str(row["qrels"]).strip() if "qrels" in row else "{}",
            "ground_truth": str(row["ground_truth"]).strip(),
            "contexts_ground_truth": str(row["contexts_ground_truth"]).strip(),
        })
    print(f"✅ Loaded {len(results)} questions")
    return results


def retrieve_energy(questions, k_retrieve=40, n_top_clusters=1):
    project_root = str(Path(__file__).parent.parent)
    from ingestion.model_embedding import vn_embedder

    print("📂 Đang load embeddings và doc_ids...")
    with open(os.path.join(project_root, "doc_ids.json"), "r") as f:
        doc_ids = json.load(f)
    all_embeddings = np.load(os.path.join(project_root, "msmarco_embeddings.npy"))
    
    embeddings_model = vn_embedder.get_model()

    print("📂 Đang load text từ ir_datasets...")
    dataset = ir_datasets.load("msmarco-passage")
    docs_store = dataset.docs_store()

    # Tạo Mock VectorStore (Thay vì Chroma thì truyền NumpyVectorStore)
    mock_db = NumpyVectorStore(doc_ids, all_embeddings, docs_store, embeddings_model)

    print("⚡ Khởi tạo EnergyRetriever (giữ nguyên thuật toán lõi của bạn)...")
    energy_retriever = EnergyRetriever(
        vector_store=mock_db,
        embeddings_model=embeddings_model,
        k_retrieve=k_retrieve,
        n_top_clusters=n_top_clusters,
    )
    
    results = []
    for i, q in enumerate(questions, 1):
        question = q["question"]
        print(f"\n{'─'*40}")
        print(f"📝 [{i}/{len(questions)}] {question[:80]}...")

        # Chạy nguyên bản thuật toán của bạn!
        docs = energy_retriever.retrieve(query=question)
        contexts = [doc.page_content for doc in docs]
        retrieved_doc_ids = [doc.metadata.get("id", "") for doc in docs]

        results.append({
            "query_id": q.get("query_id", ""),
            "question": question,
            "qrels": q.get("qrels", "{}"),
            "ground_truth": q["ground_truth"],
            "contexts_ground_truth": q["contexts_ground_truth"],
            "contexts_answer": str(contexts),
            "retrieved_doc_ids": json.dumps(retrieved_doc_ids, ensure_ascii=False),
        })

    return results


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Eval Custom Energy KMeans trên MS MARCO")
    parser.add_argument("--max", type=int, default=None)
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--k_retrieve", type=int, default=40)
    parser.add_argument("--n_clusters", type=int, default=1)
    args = parser.parse_args()

    project_root = str(Path(__file__).parent.parent)
    excel_path = os.path.join(os.path.dirname(__file__), "ms_marco_eval.xlsx")
    if not os.path.exists(excel_path):
        excel_path = os.path.join(project_root, "scoring", "ms_marco_eval.xlsx")

    print(f"\n{'='*60}")
    print(f"🎯 ĐÁNH GIÁ ENERGY KMEANS TRÊN MS MARCO (TREC DL 2019)")
    print(f"{'='*60}")

    qa_list = load_questions(excel_path, max_questions=args.max)
    results = retrieve_energy(qa_list, k_retrieve=args.k_retrieve, n_top_clusters=args.n_clusters)

    output_file = os.path.join(os.path.dirname(__file__), "eval_energy.xlsx")
    df = pd.DataFrame(results)
    df.to_excel(output_file, index=False)
    print(f"\n📁 Kết quả đã lưu: {output_file}")

    file_path, mrr_value = mrr_excel(output_file, k=args.k)
    file_path, ndcg_value = ndcg_excel(file_path, k=args.k)

    print(f"\n{'='*60}")
    print(f"✅ KẾT QUẢ ENERGY KMEANS")
    print(f"{'='*60}")
    print(f"   📈 NDCG@{args.k} = {ndcg_value:.4f}")
    print(f"   📈 MRR@{args.k}  = {mrr_value:.4f}")
    print(f"   📁 Output:  {file_path}\n")

if __name__ == "__main__":
    main()
