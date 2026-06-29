import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scoring.evaluation_metric.rouge_n import rouge_excel
from scoring.evaluation_metric.bleu import bleu_excel
from scoring.evaluation_metric.cosine_similarity import cosine_excel
from scoring.evaluation_metric.mrr import mrr_excel
from scoring.evaluation_metric.hit_rate import hit_rate_excel
from scoring.evaluation_metric.ndcg import ndcg_excel


PROJECT_ROOT = Path(__file__).resolve().parents[2]
GT2_MUTIQUERY_MAX_VALUES = (2, 3, 4, 5)


def resolve_eval_file(file_arg, pipeline, max_queries):
    """Resolve file chấm điểm; ``max_queries`` tính cả câu hỏi gốc."""
    if file_arg:
        return Path(file_arg)

    if pipeline == "gt2_mutiquery":
        return PROJECT_ROOT / "Gt2_mutiquery" / f"Gt2_mutiquery_MAX{max_queries}_eval_results.xlsx"

    return Path(__file__).parent / "eval_1000_questions.xlsx"


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
        "pipeline",
        nargs="?",
        type=str.lower,
        choices=("gt2_mutiquery",),
        help="Pipeline cần chấm; hiện hỗ trợ lệnh rút gọn: gt2_mutiquery --max N",
    )
    parser.add_argument(
        "--file",
        default=None,
        help="Đường dẫn file Excel; nếu truyền thì ưu tiên hơn pipeline và --max",
    )
    parser.add_argument(
        "--max",
        "-max",
        dest="max_queries",
        type=int,
        choices=GT2_MUTIQUERY_MAX_VALUES,
        help="Tổng số query vector của Gt2_mutiquery, đã gồm câu hỏi gốc (2, 3, 4 hoặc 5)",
    )
    args = parser.parse_args()

    if args.pipeline == "gt2_mutiquery" and args.max_queries is None and not args.file:
        parser.error("gt2_mutiquery yêu cầu --max với một trong các giá trị: 2, 3, 4, 5")
    if args.max_queries is not None and args.pipeline != "gt2_mutiquery" and not args.file:
        parser.error("--max chỉ được dùng cùng pipeline gt2_mutiquery")

    eval_file = resolve_eval_file(args.file, args.pipeline, args.max_queries)
    if eval_file.exists():
        embeddings = vn_embedder.get_model()
        result = evaluate_results(str(eval_file), embeddings)
        print(f"📁 Kết quả lưu tại: {result}")
    else:
        print(f"❌ Không tìm thấy file: {eval_file}")
        if args.pipeline == "gt2_mutiquery":
            max_parts = args.max_queries - 1
            output_path = f"Gt2_mutiquery/Gt2_mutiquery_MAX{args.max_queries}_eval_results.xlsx"
            print("Hãy sinh file Gt2_mutiquery trước bằng lệnh:")
            print(
                "python -m Gt2_mutiquery.create_eval "
                f"--max-parts {max_parts} --output {output_path}"
            )
