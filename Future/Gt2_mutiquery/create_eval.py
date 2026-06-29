"""
Gt2_mutiquery — LLM Auto Split → Multi-Vector ERC.

Pipeline: câu hỏi → LLM tự tách 1-4 sub-queries → multi-vector ERC → grade → generate.

Cách dùng:
    python -m Gt2_mutiquery.create_eval --max 50
    python Gt2_mutiquery/create_eval.py --output Gt2_mutiquery_results.xlsx
    python Gt2_mutiquery/create_eval.py --start 991   # tiếp tục từ câu 991
"""

from __future__ import annotations

# Bootstrap: hỗ trợ cả `python -m` và `python Gt2_mutiquery/create_eval.py`
if __name__ == "__main__" and __package__ is None:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    __package__ = "Gt2_mutiquery"

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

from .query_splitter import LLMAutoSplitter
from .retriever import MultiVectorERC


def main() -> None:
    parser = argparse.ArgumentParser(description="Gt2_mutiquery: LLM Auto Split → Multi-Vector ERC")
    parser.add_argument("--input", default=str(PROJECT_ROOT / "scoring" / "file 1000 cau hoi.xlsx"))
    parser.add_argument("--output", default=str(HERE / "Gt2_mutiquery_eval_results.xlsx"))
    parser.add_argument("--max", type=int, default=None)
    parser.add_argument("--start", type=int, default=0,
                        help="Bỏ qua N câu đầu (1-indexed). Ví dụ: --start 991 để tiếp tục từ câu 991.")
    parser.add_argument("--max-parts", type=int, default=4, help="Tối đa sub-queries LLM được tạo")
    parser.add_argument("--vector-store", default=str(PROJECT_ROOT / "chroma_economy_db"))
    parser.add_argument("--llm-provider", default="openai")
    parser.add_argument("--save-every", type=int, default=1)
    args = parser.parse_args()

    llm = LLM().get_llm(args.llm_provider)
    embeddings = vn_embedder.get_model()
    vector_store = Chroma(persist_directory=args.vector_store, embedding_function=embeddings)

    splitter = LLMAutoSplitter(llm=llm, max_parts=args.max_parts)
    retriever = MultiVectorERC(vector_store, embeddings)

    def retrieve_fn(question: str):
        parts = splitter.split(question)
        print(f"   -> {len(parts)} query parts: {parts}")
        return retriever.retrieve(parts), parts

    run_eval(
        retrieve_fn=retrieve_fn,
        llm=llm,
        algorithm="Gt2_mutiquery_llm_auto_split_erc",
        input_path=args.input,
        output_path=args.output,
        max_questions=args.max,
        start_from=args.start,
        save_every=args.save_every,
    )


if __name__ == "__main__":
    main()
