"""Generate GT1 single-vector ERC evaluation results."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from chatbot.utils.llm import LLM
from ingestion.model_embedding import vn_embedder
from ingestion.single_vector_retriever import SingleVectorERC
from langchain_chroma import Chroma
from scoring.eval_runner import run_eval


def main() -> None:
    parser = argparse.ArgumentParser(
        description="GT1: single query vector, K-Means, Energy Distance"
    )
    parser.add_argument(
        "--input",
        default=str(PROJECT_ROOT / "scoring" / "file 1000 cau hoi.xlsx"),
    )
    parser.add_argument(
        "--output",
        default=str(PROJECT_ROOT / "scoring" / "GT1_eval_results.xlsx"),
    )
    parser.add_argument("--max", type=int, default=None)
    parser.add_argument(
        "--start",
        type=int,
        default=0,
        help="Bo qua N-1 cau dau va tiep tuc tu cau N.",
    )
    parser.add_argument(
        "--vector-store",
        default=str(PROJECT_ROOT / "chroma_economy_db"),
    )
    parser.add_argument("--llm-provider", default="openai")
    parser.add_argument("--save-every", type=int, default=1)
    args = parser.parse_args()

    llm = LLM().get_llm(args.llm_provider)
    embeddings = vn_embedder.get_model()
    vector_store = Chroma(
        persist_directory=args.vector_store,
        embedding_function=embeddings,
    )
    retriever = SingleVectorERC(vector_store, embeddings)

    def retrieve_fn(question: str):
        docs = retriever.retrieve(question)
        return docs, retriever.last_query_parts

    run_eval(
        retrieve_fn=retrieve_fn,
        llm=llm,
        algorithm=retriever.last_algorithm,
        input_path=args.input,
        output_path=args.output,
        max_questions=args.max,
        start_from=args.start,
        save_every=args.save_every,
    )


if __name__ == "__main__":
    main()
