import argparse
import json
import os
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from chatbot.main import ChatbotRunner
from scoring_ms_marco.common import parse_list


def _to_str(value):
    return str(value).strip() if value is not None else ""


def load_questions_from_excel(excel_path, max_questions=None):
    df = pd.read_excel(excel_path)
    if max_questions:
        df = df.head(max_questions)

    rows = []
    for _, row in df.iterrows():
        rows.append(
            {
                "query_id": _to_str(row.get("query_id", "")),
                "question": _to_str(row.get("question", "")),
                "relevant_doc_ids": parse_list(row.get("relevant_doc_ids", "[]")),
                "contexts_ground_truth": parse_list(row.get("contexts_ground_truth", "[]")),
            }
        )

    print(f"Loaded {len(rows)} questions from {excel_path}")
    return rows


def create_evaluation_file(
    questions,
    output_file="eval_data_ms_marco.xlsx",
    path_vector_store="./chroma_ms_marco_db",
    llm_provider="openai",
):
    print("Initializing chatbot...")
    chatbot = ChatbotRunner(path_vector_store=path_vector_store, llm_provider=llm_provider)

    results = []
    total = len(questions)
    for idx, item in enumerate(questions, start=1):
        question = item["question"]
        print(f"[{idx}/{total}] {question}")

        input_state = {
            "question": question,
            "generation": "",
            "documents": [],
            "prompt": (
                "You are a QA assistant. Answer strictly from provided context. "
                "If not enough information, say so clearly."
            ),
        }

        try:
            output_state = chatbot.compiled_workflow.invoke(input_state)
            answer = output_state.get("generation", "")
            documents = output_state.get("documents", [])

            metadata = [doc.metadata for doc in documents]
            contexts = [doc.page_content for doc in documents]
            retrieved_doc_ids = [
                str(meta.get("doc_id", "")).strip()
                for meta in metadata
                if str(meta.get("doc_id", "")).strip()
            ]

            results.append(
                {
                    "query_id": item["query_id"],
                    "question": question,
                    "relevant_doc_ids": json.dumps(item["relevant_doc_ids"], ensure_ascii=False),
                    "contexts_ground_truth": json.dumps(item["contexts_ground_truth"], ensure_ascii=False),
                    "answer": answer,
                    "contexts_answer": json.dumps(contexts, ensure_ascii=False),
                    "metadata": json.dumps(metadata, ensure_ascii=False),
                    "retrieved_doc_ids": json.dumps(retrieved_doc_ids, ensure_ascii=False),
                }
            )
        except Exception as exc:
            results.append(
                {
                    "query_id": item["query_id"],
                    "question": question,
                    "relevant_doc_ids": json.dumps(item["relevant_doc_ids"], ensure_ascii=False),
                    "contexts_ground_truth": json.dumps(item["contexts_ground_truth"], ensure_ascii=False),
                    "answer": f"ERROR: {exc}",
                    "contexts_answer": "[]",
                    "metadata": "[]",
                    "retrieved_doc_ids": "[]",
                }
            )

    output_path = os.path.join(os.path.dirname(__file__), output_file)
    pd.DataFrame(results).to_excel(output_path, index=False)
    print(f"Saved {len(results)} rows: {output_path}")
    return output_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create MS MARCO eval_data from chatbot")
    parser.add_argument("--input", type=str, default="ms_marco_eval.xlsx")
    parser.add_argument("--output", type=str, default="eval_data_ms_marco.xlsx")
    parser.add_argument("--max", type=int, default=None)
    parser.add_argument("--vector-store", type=str, default="./chroma_ms_marco_db")
    parser.add_argument("--llm", type=str, default="openai")
    args = parser.parse_args()

    input_path = args.input
    if not os.path.isabs(input_path):
        input_path = os.path.join(os.path.dirname(__file__), input_path)

    if not os.path.exists(input_path):
        print(f"Input file not found: {input_path}")
        sys.exit(1)

    question_rows = load_questions_from_excel(input_path, max_questions=args.max)
    create_evaluation_file(
        question_rows,
        output_file=args.output,
        path_vector_store=args.vector_store,
        llm_provider=args.llm,
    )
