"""
Shared evaluation harness cho 3 pipeline GT1/GT2/GT3.

Mỗi pipeline chỉ cần cung cấp `retrieve_fn(question) -> (docs, query_parts)`.
Eval runner lo phần loading questions, grading, generating, lưu Excel.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Callable

import pandas as pd

from chatbot.utils.answer_generator import AnswerGeneratorDocs
from chatbot.utils.document_grader import DocumentGrader

NO_ANSWER = "Xin lỗi, tôi không tìm thấy thông tin liên quan trong cơ sở dữ liệu."
BASE_COLUMNS = [
    "question", "ground_truth", "contexts_ground_truth",
    "answer", "contexts_answer", "metadata",
    "query_parts", "algorithm",
]


def _text(value: Any) -> str:
    return "" if pd.isna(value) else str(value).strip()


def load_questions(excel_path: str | Path, max_q: int | None = None) -> list[dict]:
    df = pd.read_excel(excel_path)
    required = ["question", "ground_truth", "contexts_ground_truth"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"File thiếu cột: {missing}")
    if max_q:
        df = df.head(max_q)
    rows = [
        {
            "question": _text(r["question"]),
            "ground_truth": _text(r["ground_truth"]),
            "contexts_ground_truth": _text(r["contexts_ground_truth"]),
        }
        for _, r in df.iterrows()
        if _text(r["question"])
    ]
    print(f"✅ Loaded {len(rows)} câu hỏi từ {excel_path}")
    return rows


def _generate_answer(generator: AnswerGeneratorDocs, question: str, docs: list) -> str:
    if not docs:
        return NO_ANSWER
    context = "\n\n".join(d.page_content for d in docs)
    answer = generator.get_chain().invoke({"question": question, "context": context})
    return re.sub(r"<think>.*?</think>", "", answer, flags=re.DOTALL).strip()


def run_eval(
    retrieve_fn: Callable[[str], tuple[list, list[str]]],
    *,
    llm: Any,
    algorithm: str,
    input_path: str | Path,
    output_path: str | Path,
    max_questions: int | None = None,
    start_from: int = 0,
    save_every: int = 1,
    extra_columns: dict[str, Any] | None = None,
) -> str:
    """
    Args:
        retrieve_fn: Hàm pipeline-specific. Nhận question, trả về (docs, query_parts).
        llm: LLM dùng cho grader + generator.
        algorithm: Tên thuật toán (lưu vào cột algorithm).
        input_path: File Excel chứa câu hỏi.
        output_path: File Excel xuất kết quả.
        max_questions: Giới hạn số câu hỏi (test nhanh).
        start_from: Bỏ qua N câu đầu (1-indexed). Dùng khi tiếp tục sau khi bị ngắt.
        save_every: Lưu Excel sau mỗi N câu (chống mất dữ liệu).
        extra_columns: Cột phụ (vd: {"num_queries": 2}) — gắn vào mọi row.
    """
    grader = DocumentGrader(llm)
    generator = AnswerGeneratorDocs(llm)

    qa_list = load_questions(input_path, max_questions)
    columns = list(BASE_COLUMNS) + list((extra_columns or {}).keys())
    output_path = Path(output_path)

    # Nếu start_from > 0: load kết quả cũ, chỉ chạy lại từ câu start_from
    if start_from > 0 and output_path.exists():
        existing_df = pd.read_excel(output_path)
        results: list[dict] = existing_df.to_dict("records")
        print(f"📂 Loaded {len(results)} kết quả cũ từ {output_path}")
        # Cắt bỏ các hàng từ start_from trở đi để ghi đè
        results = results[: start_from - 1]
        qa_list = qa_list[start_from - 1 :]
        print(f"▶️  Tiếp tục từ câu {start_from} ({len(qa_list)} câu còn lại)")
    else:
        results = []

    base_idx = start_from if start_from > 0 else 0
    total = base_idx + len(qa_list)

    for idx, item in enumerate(qa_list, start_from if start_from > 0 else 1):
        q = item["question"]
        gt = item["ground_truth"]
        ctx_gt = item["contexts_ground_truth"]

        print(f"\n{'=' * 60}")
        print(f"📝 [{idx}/{total}] {q}")
        print(f"{'=' * 60}")

        try:
            docs, query_parts = retrieve_fn(q)
            filtered = grader.grade_batch(question=q, retrieved_docs=docs)
            print(f"   -> Giữ {len(filtered)}/{len(docs)} docs sau grade")
            answer = _generate_answer(generator, q, filtered)
            row = {
                "question": q,
                "ground_truth": gt,
                "contexts_ground_truth": str([ctx_gt]) if ctx_gt else "[]",
                "answer": answer,
                "contexts_answer": str([d.page_content for d in filtered]),
                "metadata": str([d.metadata for d in filtered]) if filtered else "",
                "query_parts": str(query_parts),
                "algorithm": algorithm,
            }
            print("✅ Xong")
        except Exception as exc:
            print(f"❌ Lỗi: {exc}")
            row = {
                "question": q,
                "ground_truth": gt,
                "contexts_ground_truth": str([ctx_gt]) if ctx_gt else "[]",
                "answer": f"ERROR: {exc}",
                "contexts_answer": "[]",
                "metadata": "",
                "query_parts": "[]",
                "algorithm": algorithm,
            }

        row.update(extra_columns or {})
        results.append(row)

        if save_every > 0 and idx % save_every == 0:
            pd.DataFrame(results, columns=columns).to_excel(output_path, index=False)

    pd.DataFrame(results, columns=columns).to_excel(output_path, index=False)
    print(f"\n✅ Đã lưu {len(results)} kết quả vào: {output_path}")
    return str(output_path)
