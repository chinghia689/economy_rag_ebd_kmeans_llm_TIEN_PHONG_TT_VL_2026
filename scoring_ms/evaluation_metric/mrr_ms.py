"""
MRR@k (Mean Reciprocal Rank) cho MS MARCO (TREC DL 2019).

Đánh giá chuẩn theo Document ID và hệ thống Qrels:
    - retrieved_doc_ids: Danh sách các doc_id do hệ thống truy xuất được.
    - qrels: Tham chiếu chuẩn từ chuyên gia NIST (Dictionary map doc_id -> relevance score).

Quy ước của TREC: 
Văn bản được xem là THỰC SỰ ĐÚNG (Relevant target) cho các binary metric (như MRR)
phải có relevance score >= 2 (Highly Relevant hoặc Perfectly Relevant).
"""

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


def reciprocal_rank(qrels, retrieved_doc_ids, k=5, threshold=2):
    """
    Tính Reciprocal Rank (RR) cho một truy vấn theo Document IDs.

    Args:
        qrels (dict): Dictionary map {doc_id: relevance}.
        retrieved_doc_ids (list[str]): Danh sách top-k doc_ids.
        k (int): Chỉ xét top-k kết quả đầu.
        threshold (int): Ngưỡng điểm để coi là relevant (>=2).
    """
    if not isinstance(qrels, dict) or not isinstance(retrieved_doc_ids, list):
        return 0.0

    top_k = retrieved_doc_ids[:k]

    # Duyệt từng doc_id theo thứ tự từ trên xuống dưới
    for idx, doc_id in enumerate(top_k, start=1):
        rel_score = qrels.get(str(doc_id), 0)
        
        # Nếu văn bản có điểm >= 2 (Highly relevant) 
        if rel_score >= threshold:
            return 1.0 / idx  # trả về nghịch đảo vị trí Rank
            
    return 0.0


def mrr_excel(file_path, k=5, out: str = None):
    """
    Đọc file Excel, tính MRR@k chuẩn theo Document ID và lưu kết quả.
    """
    df = pd.read_excel(file_path)

    if "retrieved_doc_ids" not in df.columns or "qrels" not in df.columns:
        print("❌ Lỗi: File Excel thiếu cột 'retrieved_doc_ids' hoặc 'qrels'.")
        print("💡 Hãy chạy lại lệnh eval script để sinh data chuẩn!")
        return file_path, 0.0

    # === Tính Reciprocal Rank cho từng dòng ===
    df[f"MRR@{k}"] = df.apply(
        lambda row: reciprocal_rank(
            safe_json_loads(row.get("qrels", "{}"), default={}), 
            safe_json_loads(row.get("retrieved_doc_ids", "[]"), default=[]), 
            k=k,
            threshold=2  # NIST quy định rel >= 2 mới là hoàn toàn liên quan
        ),
        axis=1,
    )

    # === Tính MRR@k toàn cục ===
    mrr_value = df[f"MRR@{k}"].mean()
    print(f"✅ MRR@{k} = {mrr_value:.4f}")

    # === Tạo đường dẫn output ===
    if not out:
        dir_name = os.path.dirname(file_path)
        base_name = os.path.basename(file_path)
        out = os.path.join(dir_name, f"mrr{k}_{base_name}")

    df.to_excel(out, index=False)
    print(f"✅ Đã tạo file: {out}")

    return out, mrr_value
