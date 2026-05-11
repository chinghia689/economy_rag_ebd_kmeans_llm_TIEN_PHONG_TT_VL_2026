import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCORING_DIR = Path(__file__).resolve().parent
DEFAULT_INPUT_FILE = SCORING_DIR / "file 1000 cau hoi.xlsx"
DEFAULT_VECTOR_STORE = PROJECT_ROOT / "chroma_economy_db"
DEFAULT_OUTPUT_FILE = "eval_1000_questions.xlsx"

sys.path.insert(0, str(PROJECT_ROOT))

from chatbot.main import ChatbotRunner


OUTPUT_COLUMNS = [
    "question",
    "ground_truth",
    "contexts_ground_truth",
    "answer",
    "contexts_answer",
    "metadata",
    "query_parts",
    "retrieval_debug",
    "algorithm",
]


def _text(value: Any) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def _output_path(output_file: str | Path) -> Path:
    path = Path(output_file)
    if path.is_absolute():
        return path
    return SCORING_DIR / path


def load_questions_from_excel(
    excel_path: str | Path,
    max_questions: int | None = None,
) -> list[dict[str, str]]:
    df = pd.read_excel(excel_path)
    required_columns = ["question", "ground_truth", "contexts_ground_truth"]
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise ValueError(f"File thiếu cột: {missing_columns}")

    if max_questions is not None:
        df = df.head(max_questions)

    results: list[dict[str, str]] = []
    for _, row in df.iterrows():
        question = _text(row["question"])
        if not question:
            continue

        results.append(
            {
                "question": question,
                "ground_truth": _text(row["ground_truth"]),
                "contexts_ground_truth": _text(row["contexts_ground_truth"]),
            }
        )

    print(f"✅ Loaded {len(results)} questions from {excel_path}")
    return results


def _write_results(results: list[dict[str, Any]], output_path: Path) -> None:
    df = pd.DataFrame(results, columns=OUTPUT_COLUMNS)
    df.to_excel(output_path, index=False)


def create_evaluation_file(
    questions: list[str],
    output_file: str = DEFAULT_OUTPUT_FILE,
    ground_truths: dict[str, str] | None = None,
    contexts_gt: dict[str, str] | None = None,
    vector_store: str | Path = DEFAULT_VECTOR_STORE,
    llm_provider: str = "openai",
    save_every: int = 1,
) -> str:
    output_path = _output_path(output_file)

    print("🚀 Đang khởi tạo chatbot...")
    chatbot = ChatbotRunner(
        path_vector_store=str(vector_store),
        llm_provider=llm_provider,
    )

    results: list[dict[str, Any]] = []

    for index, question in enumerate(questions, 1):
        print(f"\n{'=' * 60}")
        print(f"📝 [{index}/{len(questions)}] Câu hỏi: {question}")
        print(f"{'=' * 60}")

        input_state = {
            "question": question,
            "generation": "",
            "documents": [],
            "prompt": "Bạn là một chuyên gia tư vấn kinh tế Việt Nam. Hãy trả lời câu hỏi CHỈ dựa trên thông tin trong ngữ cảnh được cung cấp. Nếu ngữ cảnh không chứa thông tin cần thiết, hãy nói rõ là không có thông tin.",
        }
        gt = ground_truths.get(question, "") if ground_truths else ""
        ctx_gt = contexts_gt.get(question, "") if contexts_gt else ""

        try:
            output_state = chatbot.compiled_workflow.invoke(input_state)
            answer = output_state.get("generation", "")
            documents = output_state.get("documents", [])
            query_parts = output_state.get("query_parts", [])
            retrieval_debug = output_state.get("retrieval_debug", [])
            algorithm = output_state.get("algorithm", "")

            results.append(
                {
                    "question": question,
                    "ground_truth": gt,
                    "contexts_ground_truth": str([ctx_gt]) if ctx_gt else "[]",
                    "answer": answer,
                    "contexts_answer": str([doc.page_content for doc in documents]),
                    "metadata": str([doc.metadata for doc in documents]) if documents else "",
                    "query_parts": str(query_parts),
                    "retrieval_debug": _json(retrieval_debug),
                    "algorithm": algorithm,
                }
            )
            print("✅ Đã xử lý thành công")
        except Exception as exc:
            print(f"❌ Lỗi: {exc}")
            results.append(
                {
                    "question": question,
                    "ground_truth": gt,
                    "contexts_ground_truth": str([ctx_gt]) if ctx_gt else "[]",
                    "answer": f"ERROR: {exc}",
                    "contexts_answer": "[]",
                    "metadata": "",
                    "query_parts": "[]",
                    "retrieval_debug": "[]",
                    "algorithm": "",
                }
            )

        if save_every > 0 and index % save_every == 0:
            _write_results(results, output_path)

    _write_results(results, output_path)

    print(f"\n{'=' * 60}")
    print(f"✅ Đã lưu {len(results)} kết quả vào: {output_path}")
    print("   Sau đó chạy: python scoring/main.py")
    print(f"{'=' * 60}")
    return str(output_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Tạo file evaluation từ full RAG pipeline")
    parser.add_argument("--source", choices=["excel"], default="excel")
    parser.add_argument("--input", default=str(DEFAULT_INPUT_FILE))
    parser.add_argument("--output", default=DEFAULT_OUTPUT_FILE)
    parser.add_argument("--max", type=int, default=None)
    parser.add_argument("--vector-store", default=str(DEFAULT_VECTOR_STORE))
    parser.add_argument("--llm-provider", default="openai")
    parser.add_argument("--save-every", type=int, default=1)
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"❌ Không tìm thấy file: {args.input}")
        sys.exit(1)

    qa_list = load_questions_from_excel(args.input, max_questions=args.max)
    questions = [item["question"] for item in qa_list]
    ground_truths = {item["question"]: item["ground_truth"] for item in qa_list}
    contexts_gt = {item["question"]: item["contexts_ground_truth"] for item in qa_list}

    create_evaluation_file(
        questions=questions,
        output_file=args.output,
        ground_truths=ground_truths,
        contexts_gt=contexts_gt,
        vector_store=args.vector_store,
        llm_provider=args.llm_provider,
        save_every=args.save_every,
    )


if __name__ == "__main__":
    main()
