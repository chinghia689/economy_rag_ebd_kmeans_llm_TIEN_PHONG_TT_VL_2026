"""
Đánh giá retrieval BM25 + E5 (Hybrid Retrieval) trên MS MARCO.

Dùng in-memory numpy DB.
"""

import os
import sys
import json
import numpy as np
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import ir_datasets
from rank_bm25 import BM25Okapi
from sklearn.metrics.pairwise import cosine_similarity
from scoring_ms.evaluation_metric.ndcg_ms import ndcg_excel
from scoring_ms.evaluation_metric.mrr_ms import mrr_excel


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


def reciprocal_rank_fusion(bm25_indices, e5_indices, k_rrf=60):
    scores = {}
    for rank, idx in enumerate(bm25_indices):
        scores[idx] = scores.get(idx, 0) + 1.0 / (k_rrf + rank + 1)
    for rank, idx in enumerate(e5_indices):
        scores[idx] = scores.get(idx, 0) + 1.0 / (k_rrf + rank + 1)
    sorted_indices = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
    return sorted_indices


def retrieve_bm25_e5(questions, k_retrieve=10, k_bm25=20, k_e5=20):
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

    all_docs_text = []
    for doc_id in doc_ids:
        try:
            doc = docs_store.get(doc_id)
            all_docs_text.append(doc.text)
        except:
            all_docs_text.append("")

    print("🔤 Đang tokenize corpus cho BM25...")
    tokenized_corpus = [text.lower().split() for text in all_docs_text]
    bm25 = BM25Okapi(tokenized_corpus)
    print("✅ BM25 + E5 Hybrid Retriever sẵn sàng!")

    results = []
    for i, q in enumerate(questions, 1):
        question = q["question"]

        if i % 50 == 0 or i == 1:
            print(f"   🔍 [{i}/{len(questions)}] Đang retrieve...")

        tokenized_query = question.lower().split()
        bm25_scores = bm25.get_scores(tokenized_query)
        bm25_top_indices = np.argsort(bm25_scores)[::-1][:k_bm25]

        query_vec = np.array(embeddings_model.embed_query(question)).reshape(1, -1)
        sims = cosine_similarity(query_vec, all_embeddings)[0]
        e5_top_indices = np.argsort(sims)[::-1][:k_e5]

        merged_indices = reciprocal_rank_fusion(bm25_top_indices.tolist(), e5_top_indices.tolist())
        final_indices = merged_indices[:k_retrieve]
        contexts = [all_docs_text[idx] for idx in final_indices]
        retrieved_doc_ids = [doc_ids[idx] for idx in final_indices]

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
    parser = argparse.ArgumentParser(description="Đánh giá BM25+E5 trên MS MARCO")
    parser.add_argument("--max", type=int, default=None)
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--k_retrieve", type=int, default=10)
    parser.add_argument("--k_bm25", type=int, default=20)
    parser.add_argument("--k_e5", type=int, default=20)
    args = parser.parse_args()

    project_root = str(Path(__file__).parent.parent)
    excel_path = os.path.join(os.path.dirname(__file__), "ms_marco_eval.xlsx")
    if not os.path.exists(excel_path):
        excel_path = os.path.join(project_root, "scoring", "ms_marco_eval.xlsx")

    qa_list = load_questions(excel_path, max_questions=args.max)
    results = retrieve_bm25_e5(qa_list, k_retrieve=args.k_retrieve, k_bm25=args.k_bm25, k_e5=args.k_e5)

    output_file = os.path.join(os.path.dirname(__file__), "eval_bm25_e5.xlsx")
    df = pd.DataFrame(results)
    df.to_excel(output_file, index=False)
    print(f"📁 Kết quả đã lưu: {output_file}")

    file_path, mrr_value = mrr_excel(output_file, k=args.k)
    file_path, ndcg_value = ndcg_excel(file_path, k=args.k)

    print(f"\n{'='*60}")
    print(f"✅ KẾT QUẢ BM25+E5 TRÊN MS MARCO")
    print(f"{'='*60}")
    print(f"   📈 NDCG@{args.k} = {ndcg_value:.4f}")
    print(f"   📈 MRR@{args.k}  = {mrr_value:.4f}")
    print(f"   📁 Output:  {file_path}\n")

if __name__ == "__main__":
    main()
