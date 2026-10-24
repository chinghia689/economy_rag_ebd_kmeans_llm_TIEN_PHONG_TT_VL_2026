"""Evaluate multilingual-E5 cosine top-k retrieval without the ERC step.

The script reuses the project's Chroma index and relevance functions. It does
not write an output workbook. Keep the question set and index outside Git if
they are too large or have distribution restrictions.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import pandas as pd
from langchain_chroma import Chroma

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from ingestion.model_embedding import vn_embedder  # noqa: E402
from scoring.evaluation_metric.hit_rate import hit_rate  # noqa: E402
from scoring.evaluation_metric.mrr import reciprocal_rank  # noqa: E402
from scoring.evaluation_metric.ndcg import (  # noqa: E402
    ndcg_at_k,
    relevance_graded,
)


def evaluate(
    input_path: Path,
    vector_store_path: Path,
    *,
    k: int = 5,
    batch_size: int = 64,
) -> dict[str, float]:
    questions_df = pd.read_excel(input_path).fillna("")
    required = {"question", "ground_truth"}
    missing = required.difference(questions_df.columns)
    if missing:
        raise ValueError(f"Question workbook is missing columns: {sorted(missing)}")

    questions = questions_df["question"].astype(str).str.strip().tolist()
    ground_truths = questions_df["ground_truth"].astype(str).str.strip().tolist()
    if not questions:
        raise ValueError("The question workbook contains no rows.")

    embeddings = vn_embedder.get_model()
    vector_store = Chroma(
        persist_directory=str(vector_store_path),
        embedding_function=embeddings,
    )
    retrieved_contexts: list[list[str]] = []
    started = time.perf_counter()

    for offset in range(0, len(questions), batch_size):
        batch = questions[offset : offset + batch_size]
        # E5 requires query: for questions. Embed the batch in one model call.
        query_vectors = embeddings._base.embed_documents(
            ["query: " + question for question in batch]
        )
        response = vector_store._collection.query(
            query_embeddings=query_vectors,
            n_results=k,
            include=["documents"],
        )
        retrieved_contexts.extend(response["documents"])

    reciprocal_ranks = [
        reciprocal_rank(gold, contexts)
        for gold, contexts in zip(ground_truths, retrieved_contexts)
    ]
    hit_rates = [
        hit_rate(gold, contexts, k=k)
        for gold, contexts in zip(ground_truths, retrieved_contexts)
    ]
    ndcgs = []
    for gold, contexts in zip(ground_truths, retrieved_contexts):
        relevances = [relevance_graded(gold, context) for context in contexts]
        ndcgs.append(ndcg_at_k(relevances, k))

    return {
        "questions": float(len(questions)),
        "MRR": sum(reciprocal_ranks) / len(reciprocal_ranks),
        f"Hit@{k}": sum(hit_rates) / len(hit_rates),
        f"NDCG@{k}": sum(ndcgs) / len(ndcgs),
        "elapsed_seconds": time.perf_counter() - started,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate pure multilingual-E5 cosine top-k retrieval."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=PROJECT_ROOT / "scoring" / "file 1000 cau hoi.xlsx",
        help="Question workbook with question and ground_truth columns.",
    )
    parser.add_argument(
        "--vector-store",
        type=Path,
        default=PROJECT_ROOT / "chroma_economy_db",
    )
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--batch-size", type=int, default=64)
    args = parser.parse_args()

    metrics = evaluate(
        args.input,
        args.vector_store,
        k=args.k,
        batch_size=args.batch_size,
    )
    print(f"Questions: {int(metrics['questions'])}")
    print(f"MRR: {metrics['MRR']:.4f}")
    print(f"Hit@{args.k}: {metrics[f'Hit@{args.k}']:.4f}")
    print(f"NDCG@{args.k}: {metrics[f'NDCG@{args.k}']:.4f}")
    print(f"Elapsed: {metrics['elapsed_seconds']:.1f}s")


if __name__ == "__main__":
    main()
