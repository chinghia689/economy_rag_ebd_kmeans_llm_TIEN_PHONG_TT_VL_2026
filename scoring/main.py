

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scoring.evaluation_metric.rouge_n import rouge_excel
from scoring.evaluation_metric.bleu import bleu_excel
from scoring.evaluation_metric.cosine_similarity import cosine_excel
from scoring.evaluation_metric.mrr import mrr_excel
from scoring.evaluation_metric.hit_rate import hit_rate_excel
from scoring.evaluation_metric.ndcg import ndcg_excel


def evaluate_results(file_path, embeddings):
    file_path = rouge_excel(file_path, n=2)

    file_path = bleu_excel(file_path, n=2)

    file_path = cosine_excel(file_path, embeddings)

    file_path, mrr_value = mrr_excel(file_path)

    k = 5

    file_path, hit_value = hit_rate_excel(file_path, k=k)

    file_path = ndcg_excel(file_path, k=k)

    print(f"✅ Evaluation done. MRR={mrr_value} | HIT@{k}={hit_value}")

    return file_path


if __name__ == "__main__":
    from ingestion.model_embedding import vn_embedder

    parser = argparse.ArgumentParser(description="Chấm điểm file evaluation RAG")
    parser.add_argument(
        "--file",
        default=os.path.join(os.path.dirname(__file__), "eval_1000_questions.xlsx"),
    )
    args = parser.parse_args()

    embeddings = vn_embedder.get_model()

    eval_file = args.file
    if os.path.exists(eval_file):
        result = evaluate_results(eval_file, embeddings)
        print(f"📁 Kết quả lưu tại: {result}")
    else:
        print(f"❌ Không tìm thấy file: {eval_file}")
