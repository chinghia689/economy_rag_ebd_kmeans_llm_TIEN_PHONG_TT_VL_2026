"""
GT3 — LLM Fixed-N Split → Multi-Vector ERC.

Pipeline: câu hỏi → LLM tách ĐÚNG N sub-queries (N=1..4) → multi-vector ERC → grade → generate.

Tham số chính:
    --num-queries N    N = 1, 2, 3 hoặc 4 (mặc định: 2)

Cách dùng:
    python -m GT3_Manual_N.create_eval --num-queries 2 --max 50
    python GT3_Manual_N/create_eval.py --num-queries 3 --output GT3_N3.xlsx
    python GT3_Manual_N/create_eval.py --num-queries 2 --start 991   # tiếp tục từ câu 991
"""

from __future__ import annotations

# Bootstrap: hỗ trợ cả `python -m` và `python GT3_Manual_N/create_eval.py`
if __name__ == "__main__" and __package__ is None:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    __package__ = "GT3_Manual_N"

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

from .query_splitter import LLMFixedNSplitter
from .retriever import MultiVectorERC


def main() -> None:
    parser = argparse.ArgumentParser(description="GT3: LLM Fixed-N → Multi-Vector ERC")
    parser.add_argument("--input", default=str(PROJECT_ROOT / "scoring" / "file 1000 cau hoi.xlsx"))
    parser.add_argument("--output", default=None, help="Mặc định: GT3_N{N}_eval_results.xlsx")
    parser.add_argument("--num-queries", type=int, default=2, choices=[1, 2, 3, 4],
                        help="Số sub-queries cố định (1-4, mặc định: 2)")
    parser.add_argument("--max", type=int, default=None)
    parser.add_argument("--start", type=int, default=0,
                        help="Bỏ qua N câu đầu (1-indexed). Ví dụ: --start 991 để tiếp tục từ câu 991.")
    parser.add_argument("--vector-store", default=str(PROJECT_ROOT / "chroma_economy_db"))
    parser.add_argument("--llm-provider", default="openai")
    parser.add_argument("--save-every", type=int, default=1)
    args = parser.parse_args()

    output_path = args.output or str(HERE / f"GT3_N{args.num_queries}_eval_results.xlsx")

    llm = LLM().get_llm(args.llm_provider)
    embeddings = vn_embedder.get_model()
    vector_store = Chroma(persist_directory=args.vector_store, embedding_function=embeddings)

    splitter = LLMFixedNSplitter(llm=llm, num_queries=args.num_queries)
    retriever = MultiVectorERC(vector_store, embeddings)

    def retrieve_fn(question: str):
        parts = splitter.split(question)
        print(f"   -> {len(parts)} query parts (N={args.num_queries}): {parts}")
        return retriever.retrieve(parts), parts

    run_eval(
        retrieve_fn=retrieve_fn,
        llm=llm,
        algorithm=f"GT3_llm_fixed_{args.num_queries}_erc",
        input_path=args.input,
        output_path=output_path,
        max_questions=args.max,
        start_from=args.start,
        save_every=args.save_every,
        extra_columns={"num_queries": args.num_queries},
    )


if __name__ == "__main__":
    main()
