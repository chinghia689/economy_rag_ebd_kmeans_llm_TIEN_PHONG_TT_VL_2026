"""
Main scoring cho MS MARCO: chỉ chấm NDCG@5 và MRR@5.

Tương tự scoring/main.py nhưng đơn giản hơn:
    - Chỉ tính 2 metric: NDCG@5 và MRR@5
    - Phục vụ đánh giá retrieval trên MS MARCO dataset
    
Sử dụng:
    python scoring_ms/main.py
    python scoring_ms/main.py --input path/to/eval_data.xlsx
"""

import os
import sys
from pathlib import Path

# Thêm parent folder vào path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scoring_ms.evaluation_metric.ndcg_ms import ndcg_excel
from scoring_ms.evaluation_metric.mrr_ms import mrr_excel


def evaluate_ms_marco(file_path, k=5):
    """
    Chạy pipeline đánh giá MS MARCO: chỉ NDCG@5 và MRR@5.

    Args:
        file_path (str): File Excel chứa kết quả retrieval.
                         Yêu cầu cột: question, ground_truth, contexts_answer
        k (int): Top-k để tính NDCG và MRR (mặc định 5).

    Returns:
        tuple: (output_path, ndcg_value, mrr_value)
    """
    print(f"\n{'='*60}")
    print(f"📊 ĐÁNH GIÁ MS MARCO RETRIEVAL (NDCG@{k} + MRR@{k})")
    print(f"{'='*60}")
    print(f"📂 Input: {file_path}")

    # MRR@k
    file_path, mrr_value = mrr_excel(file_path, k=k)

    # NDCG@k
    file_path, ndcg_value = ndcg_excel(file_path, k=k)

    print(f"\n{'='*60}")
    print(f"✅ KẾT QUẢ ĐÁNH GIÁ MS MARCO")
    print(f"{'='*60}")
    print(f"   📈 NDCG@{k} = {ndcg_value:.4f}")
    print(f"   📈 MRR@{k}  = {mrr_value:.4f}")
    print(f"   📁 Output:  {file_path}")
    print(f"{'='*60}\n")

    return file_path, ndcg_value, mrr_value


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Chấm điểm MS MARCO (NDCG@5, MRR@5)")
    parser.add_argument("--input", type=str, default=None,
                        help="Đường dẫn file Excel input (mặc định: scoring_ms/eval_data.xlsx)")
    parser.add_argument("--k", type=int, default=5,
                        help="Top-k để tính NDCG và MRR (mặc định: 5)")
    args = parser.parse_args()

    # Xác định file input
    if args.input:
        eval_file = args.input
    else:
        eval_file = os.path.join(os.path.dirname(__file__), "eval_data.xlsx")

    if os.path.exists(eval_file):
        result_path, ndcg, mrr = evaluate_ms_marco(eval_file, k=args.k)
    else:
        print(f"❌ Không tìm thấy file: {eval_file}")
        sys.exit(1)
