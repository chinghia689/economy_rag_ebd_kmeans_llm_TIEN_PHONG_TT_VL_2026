"""
NDCG@k (Normalized Discounted Cumulative Gain) cho MS MARCO (TREC DL 2019).

Đánh giá chuẩn theo Document ID và hệ thống Qrels của NIST:
    - retrieved_doc_ids: Danh sách các doc_id do hệ thống truy xuất được.
    - qrels: Tham chiếu chuẩn từ chuyên gia NIST (Dictionary map doc_id -> relevance score).

Relevance Score do NIST đánh giá:
    0: Không liên quan
    1: Có liên quan một chút
    2: Rất liên quan
    3: Cực kỳ liên quan / Hoàn hảo
"""

import math
import os
import json
import pandas as pd


def safe_json_loads(x, default=None):
    if default is None:
        default = {}
    try:
        if isinstance(x, str):
            return json.loads(x)
        return x
    except:
        return default


def dcg_at_k(rels, k):
    """Tính Discounted Cumulative Gain tại vị trí k."""
    return sum(rel / math.log2(i + 2) for i, rel in enumerate(rels[:k]))


def ndcg_at_k(rels, qrels_dict, k):
    """
    Tính Normalized DCG tại vị trí k.
    
    Args:
        rels (list[int]): Danh sách relevance của các văn bản được retrieve.
        qrels_dict (dict): Toàn bộ Qrels của câu hỏi (để tìm IDCG thực sự).
        k (int): Top-k cần tính.
    """
    dcg = dcg_at_k(rels, k)
    
    # IDCG (Ideal DCG): Được tính bằng cách lấy k văn bản CÓ ĐIỂM CAO NHẤT trong Qrels
    ideal_rels = sorted(qrels_dict.values(), reverse=True)
    idcg = dcg_at_k(ideal_rels, k)
    
    return dcg / idcg if idcg > 0 else 0.0


def calc_ndcg_row(row, k=5):
    """Tính NDCG@k cho một dòng (câu hỏi) bằng Document IDs."""
    
    # 1. Parse qrels và retrieved_doc_ids
    qrels = safe_json_loads(row.get("qrels", "{}"), default={})
    retrieved_doc_ids = safe_json_loads(row.get("retrieved_doc_ids", "[]"), default=[])
    
    if not isinstance(retrieved_doc_ids, list) or not isinstance(qrels, dict):
        return 0.0
    
    if not qrels:
        return 0.0  # Câu hỏi không có đánh giá thực tế
        
    # 2. Sinh danh sách relevance thực tế của Top K văn bản lấy ra
    relevances = []
    for doc_id in retrieved_doc_ids[:k]:
        # Điểm mọc từ qrels, nếu không có mặt thì tự động là 0
        rel_score = qrels.get(str(doc_id), 0)
        relevances.append(rel_score)

    return ndcg_at_k(relevances, qrels, k)


def ndcg_excel(path, k=5, out=None):
    """
    Đọc file Excel, tính NDCG@k cho từng dòng và lưu kết quả.
    """
    df = pd.read_excel(path)

    if "retrieved_doc_ids" not in df.columns or "qrels" not in df.columns:
        print("❌ Lỗi: File Excel thiếu cột 'retrieved_doc_ids' hoặc 'qrels'.")
        print("💡 Hãy chạy lại lệnh eval script để sinh data mới!")
        return path, 0.0

    df[f"NDCG@{k}"] = df.apply(lambda r: calc_ndcg_row(r, k), axis=1)

    if not out:
        dir_name = os.path.dirname(path)
        base_name = os.path.basename(path)
        out = os.path.join(dir_name, f"ndcg{k}_{base_name}")

    df.to_excel(out, index=False)

    mean_ndcg = df[f"NDCG@{k}"].mean()
    print(f"✅ NDCG@{k} Done: {out}")
    print(f"📊 Mean NDCG@{k}: {mean_ndcg:.4f}")

    return out, mean_ndcg
