"""
Tạo file ms_marco_eval.xlsx cho scoring_ms.

Dùng TREC DL 2019 — 43 queries với graded relevance judgments (qrels) từ NIST assessors.
Đây là benchmark chuẩn để đánh giá retrieval trên MS MARCO passage collection.

Sử dụng:
    python scoring_ms/create_ms_marco_eval.py
"""

import os
import sys
import json
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import ir_datasets


def export_trec_dl_2019(output_path=None):
    """
    Export TREC DL 2019 queries + qrels thành file Excel cho evaluation.

    TREC DL 2019:
        - 43 queries (judged subset)
        - Graded relevance: 0 (irrelevant), 1 (related), 2 (highly relevant), 3 (perfectly relevant)
        - Dùng MS MARCO passage collection làm corpus

    Args:
        output_path (str): Đường dẫn file output.

    Returns:
        str: Đường dẫn file Excel đã tạo.
    """
    if not output_path:
        output_path = os.path.join(os.path.dirname(__file__), "ms_marco_eval.xlsx")

    print("🚀 Loading TREC DL 2019 (judged subset)...")
    dataset = ir_datasets.load("msmarco-passage/trec-dl-2019/judged")

    # 1. Load queries
    print("📋 Loading queries...")
    queries = {}
    for query in dataset.queries_iter():
        queries[query.query_id] = query.text
    print(f"   → {len(queries)} queries")

    # 2. Load qrels (relevance judgments)
    print("📋 Loading qrels (relevance judgments)...")
    qrels = defaultdict(dict)  # qrels[query_id][doc_id] = relevance
    for qrel in dataset.qrels_iter():
        qrels[qrel.query_id][qrel.doc_id] = qrel.relevance
    print(f"   → {sum(len(v) for v in qrels.values())} judgments cho {len(qrels)} queries")

    # 3. Load docs liên quan (chỉ lấy docs có relevance >= 2 làm ground truth)
    print("📋 Loading relevant passages...")
    
    # Collect tất cả doc_ids cần lấy nội dung
    relevant_doc_ids = set()
    for query_id, doc_rels in qrels.items():
        for doc_id, rel in doc_rels.items():
            if rel >= 2:  # highly relevant hoặc perfectly relevant
                relevant_doc_ids.add(doc_id)
    
    print(f"   → Cần lấy nội dung {len(relevant_doc_ids)} relevant passages")
    
    # Load nội dung passages
    doc_texts = {}
    print("📂 Loading MS MARCO passages (có thể mất vài phút lần đầu)...")
    docs_store = dataset.docs_store()
    for doc_id in relevant_doc_ids:
        try:
            doc = docs_store.get(doc_id)
            doc_texts[doc_id] = doc.text
        except Exception:
            pass
    print(f"   → Đã load {len(doc_texts)} passages")

    # 4. Build evaluation data
    rows = []
    for query_id, query_text in queries.items():
        if query_id not in qrels:
            continue

        doc_rels = qrels[query_id]

        # Ground truth: lấy passage có relevance cao nhất
        best_doc_id = max(doc_rels, key=doc_rels.get)
        best_rel = doc_rels[best_doc_id]

        # Lấy tất cả relevant passages (rel >= 2) làm contexts_ground_truth
        gt_passages = []
        for doc_id, rel in doc_rels.items():
            if rel >= 2 and doc_id in doc_texts:
                gt_passages.append(doc_texts[doc_id])

        if not gt_passages:
            # Fallback: lấy passages có rel >= 1
            for doc_id, rel in doc_rels.items():
                if rel >= 1 and doc_id in doc_texts:
                    gt_passages.append(doc_texts[doc_id])

        # Ground truth text = passage có relevance cao nhất
        ground_truth = doc_texts.get(best_doc_id, "")
        if not ground_truth and gt_passages:
            ground_truth = gt_passages[0]

        if not ground_truth:
            continue

        rows.append({
            "query_id": str(query_id),
            "question": query_text,
            "qrels": json.dumps(doc_rels, ensure_ascii=False),
            "ground_truth": ground_truth,
            "contexts_ground_truth": json.dumps(gt_passages, ensure_ascii=False),
        })

    df = pd.DataFrame(rows)
    df.to_excel(output_path, index=False)

    print(f"\n{'='*60}")
    print(f"✅ Export xong TREC DL 2019!")
    print(f"{'='*60}")
    print(f"   📊 Số queries: {len(df)}")
    print(f"   📁 Output: {output_path}")
    print(f"{'='*60}")
    return output_path


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Tạo file TREC DL 2019 eval")
    parser.add_argument("--output", type=str, default=None,
                        help="Đường dẫn file output")
    args = parser.parse_args()

    export_trec_dl_2019(output_path=args.output)
