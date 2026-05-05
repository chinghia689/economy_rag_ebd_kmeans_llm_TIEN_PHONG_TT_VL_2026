"""
Đánh giá retrieval E5 (Dense Retrieval) trên MS MARCO.

Dùng in-memory msmarco_embeddings.npy (42,791 vector x 768) + doc_ids.json

Sử dụng:
    python scoring_ms/eval_e5.py
    python scoring_ms/eval_e5.py --max 100 --k 5
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


def retrieve_e5(questions, k_retrieve=10):
    project_root = str(Path(__file__).parent.parent)
    from ingestion.model_embedding import vn_embedder

    print("📂 Đang load embeddings và doc_ids...")
    doc_ids_path = os.path.join(project_root, "doc_ids.json")
    embs_path = os.path.join(project_root, "msmarco_embeddings.npy")
    with open(doc_ids_path, "r") as f:
        doc_ids = json.load(f)
    all_embeddings = np.load(embs_path)
    print(f"   → Tổng doc_ids: {len(doc_ids)}, shape emb: {all_embeddings.shape}")

    embeddings_model = vn_embedder.get_model()

    print("📂 Đang load text từ ir_datasets...")
    dataset = ir_datasets.load("msmarco-passage")
    docs_store = dataset.docs_store()

    results = []
    for i, q in enumerate(questions, 1):
        question = q["question"]

        if i % 50 == 0 or i == 1:
            print(f"   🔍 [{i}/{len(questions)}] Đang retrieve...")

        query_vec = np.array(embeddings_model.embed_query(question)).reshape(1, -1)
        sims = cosine_similarity(query_vec, all_embeddings)[0]
        top_indices = np.argsort(sims)[::-1][:k_retrieve]

        contexts = []
        retrieved_doc_ids = []
        for idx in top_indices:
            doc_id = doc_ids[idx]
            retrieved_doc_ids.append(doc_id)
            try:
                doc = docs_store.get(doc_id)
                contexts.append(doc.text)
            except:
                pass

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

    parser = argparse.ArgumentParser(description="Đánh giá E5 trên MS MARCO")
    parser.add_argument("--max", type=int, default=None, help="Giới hạn số câu hỏi")
    parser.add_argument("--k", type=int, default=5, help="Top-k NDCG/MRR (mặc định: 5)")
    parser.add_argument("--k_retrieve", type=int, default=10, help="Số passages (mặc định: 10)")
    args = parser.parse_args()

    project_root = str(Path(__file__).parent.parent)
    excel_path = os.path.join(os.path.dirname(__file__), "ms_marco_eval.xlsx")
    if not os.path.exists(excel_path):
        excel_path = os.path.join(project_root, "scoring", "ms_marco_eval.xlsx")
    if not os.path.exists(excel_path):
        print(f"❌ Không tìm thấy file: {excel_path}")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"🎯 ĐÁNH GIÁ E5 DENSE RETRIEVAL TRÊN MS MARCO")
    print(f"{'='*60}")

    qa_list = load_questions(excel_path, max_questions=args.max)
    results = retrieve_e5(qa_list, k_retrieve=args.k_retrieve)

    output_file = os.path.join(os.path.dirname(__file__), "eval_e5.xlsx")
    df = pd.DataFrame(results)
    df.to_excel(output_file, index=False)
    print(f"📁 Kết quả đã lưu: {output_file}")

    file_path, mrr_value = mrr_excel(output_file, k=args.k)
    file_path, ndcg_value = ndcg_excel(file_path, k=args.k)

    print(f"\n{'='*60}")
    print(f"✅ KẾT QUẢ E5 TRÊN MS MARCO")
    print(f"{'='*60}")
    print(f"   📈 NDCG@{args.k} = {ndcg_value:.4f}")
    print(f"   📈 MRR@{args.k}  = {mrr_value:.4f}")
    print(f"   📁 Output:  {file_path}\n")

if __name__ == "__main__":
    main()
