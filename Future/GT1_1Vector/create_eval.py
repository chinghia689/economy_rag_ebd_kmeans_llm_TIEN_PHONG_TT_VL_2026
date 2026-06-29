"""
GT1 — Single Vector ERC.

Pipeline: câu hỏi → 1 vector → K-Means cluster docs → Energy Distance → grade → generate.

Cách dùng:
    python -m GT1_1Vector.create_eval --max 50
    python GT1_1Vector/create_eval.py --output GT1_results.xlsx
    python GT1_1Vector/create_eval.py --start 991   # tiếp tục từ câu 991
"""

from __future__ import annotations

# Bootstrap: hỗ trợ cả `python -m` và `python GT1_1Vector/create_eval.py`
if __name__ == "__main__" and __package__ is None:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    __package__ = "GT1_1Vector"

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent / "Folder_All"
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(HERE.parent / ".env")

from chatbot.utils.llm import LLM
from ingestion.model_embedding import vn_embedder
from langchain_chroma import Chroma
from scoring.eval_runner import run_eval

from .retriever import SingleVectorERC


def main() -> None:
    parser = argparse.ArgumentParser(description="GT1: Single Vector → ERC")
    parser.add_argument("--input", default=str(PROJECT_ROOT / "scoring" / "file 1000 cau hoi.xlsx"))
    parser.add_argument("--output", default=str(HERE / "GT1_eval_results.xlsx"))
    parser.add_argument("--max", type=int, default=None)
    parser.add_argument("--start", type=int, default=0,
                        help="Bỏ qua N câu đầu (1-indexed). Ví dụ: --start 991 để tiếp tục từ câu 991.")
    parser.add_argument("--vector-store", default=str(PROJECT_ROOT / "chroma_economy_db"))
    parser.add_argument("--llm-provider", default="openai")
    parser.add_argument("--save-every", type=int, default=1)
    args = parser.parse_args()

    llm = LLM().get_llm(args.llm_provider)
    embeddings = vn_embedder.get_model()
    vector_store = Chroma(persist_directory=args.vector_store, embedding_function=embeddings)
    retriever = SingleVectorERC(vector_store, embeddings)

    def retrieve_fn(question: str):
        docs = retriever.retrieve(question)
        return docs, [question]

    run_eval(
        retrieve_fn=retrieve_fn,
        llm=llm,
        algorithm="GT1_single_vector_erc",
        input_path=args.input,
        output_path=args.output,
        max_questions=args.max,
        start_from=args.start,
        save_every=args.save_every,
    )


if __name__ == "__main__":
    main()
