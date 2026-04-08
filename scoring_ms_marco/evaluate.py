import argparse
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd


# =========================
# METRICS
# =========================
def mrr_at_k(retrieved, relevant_dict, k=10):
    for rank, doc_id in enumerate(retrieved[:k], start=1):
        if doc_id in relevant_dict:
            return 1.0 / rank
    return 0.0


def hit_at_k(retrieved, relevant_dict, k=10):
    for doc_id in retrieved[:k]:
        if doc_id in relevant_dict:
            return 1.0
    return 0.0


def ndcg_at_k(retrieved, relevant_dict, k=10):
    # DCG
    gains = [relevant_dict.get(doc_id, 0.0) for doc_id in retrieved[:k]]
    dcg = sum(g / np.log2(i + 2) for i, g in enumerate(gains))

    # IDCG
    ideal = sorted(relevant_dict.values(), reverse=True)[:k]
    idcg = sum(g / np.log2(i + 2) for i, g in enumerate(ideal))

    return dcg / idcg if idcg > 0 else 0.0


# =========================
# LOAD QRELS
# =========================
def load_qrels(path):
    if not os.path.exists(path):
        raise FileNotFoundError(f"❌ Missing qrels file: {path}")

    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    qrels = {}

    for qid, value in raw.items():
        qid = str(qid)

        if isinstance(value, list):
            qrels[qid] = {str(doc_id): 1.0 for doc_id in value}

        elif isinstance(value, dict):
            qrels[qid] = {str(doc_id): float(score) for doc_id, score in value.items()}

        else:
            raise ValueError(f"❌ Invalid qrels format at query {qid}")

    return qrels


# =========================
# PARSE LIST STRING
# =========================
def parse_list(value):
    if value is None:
        return []

    # pd.isna raises on non-scalar, guard with try
    try:
        if pd.isna(value):
            return []
    except (TypeError, ValueError):
        pass

    if isinstance(value, list):
        return value

    try:
        parsed = json.loads(value)
        if not isinstance(parsed, list):
            print(f"⚠️ Parse warning: expected list, got {type(parsed).__name__} for value: {value!r}")
            return []
        return parsed
    except Exception:
        print(f"⚠️ Parse warning: could not parse value: {value!r} — treating as empty list")
        return []


# =========================
# MAIN
# =========================
def evaluate(input_path, qrels_path, output_path=None, top_k=10):
    print(f"📂 Loading file: {input_path}")

    df = pd.read_excel(input_path)

    if "query_id" not in df.columns:
        raise ValueError("❌ File phải có cột 'query_id'")

    if "retrieved_doc_ids" not in df.columns:
        raise ValueError("❌ Thiếu cột 'retrieved_doc_ids'")

    qrels = load_qrels(qrels_path)

    mrr_list = []
    hit_list = []
    ndcg_list = []
    valid_indices = []

    debug_retrieval_miss = 0
    debug_missing_qid = 0
    debug_no_relevant = 0

    for idx, row in df.iterrows():
        query_id = str(row["query_id"]).strip()

        # Skip invalid query_id
        if not query_id or query_id == "nan":
            debug_missing_qid += 1
            continue

        relevant_dict = qrels.get(query_id, {})

        # Skip query không có ground truth (chuẩn paper)
        if not relevant_dict:
            debug_no_relevant += 1
            continue

        # FIX: dùng tên biến khác để không shadow tham số top_k
        relevant_dict = {str(doc_id): v for doc_id, v in relevant_dict.items()}

        retrieved = [str(x) for x in parse_list(row["retrieved_doc_ids"])]

        if not retrieved:
            print(f"⚠️ No retrieved docs @ row {idx} | query_id={query_id}")

        mrr = mrr_at_k(retrieved, relevant_dict, top_k)
        hit = hit_at_k(retrieved, relevant_dict, top_k)
        ndcg = ndcg_at_k(retrieved, relevant_dict, top_k)

        # FIX: đổi tên thành retrieval_miss cho đúng ngữ nghĩa
        if mrr == 0:
            debug_retrieval_miss += 1
            print("\n---- RETRIEVAL MISS ----")
            print(f"Row: {idx}")
            print(f"Query ID: {query_id}")
            print(f"Relevant (first 5): {list(relevant_dict.keys())[:5]}")
            print(f"Retrieved (first 5): {retrieved[:5]}")

        mrr_list.append(mrr)
        hit_list.append(hit)
        ndcg_list.append(ndcg)
        valid_indices.append(idx)

    # =========================
    # SUMMARY
    # =========================
    mrr_mean = np.mean(mrr_list) if mrr_list else 0.0
    hit_mean = np.mean(hit_list) if hit_list else 0.0
    ndcg_mean = np.mean(ndcg_list) if ndcg_list else 0.0

    # FIX: dùng valid_indices để gán score đúng hàng
    df_valid = df.loc[valid_indices].copy()
    df_valid[f"MRR@{top_k}"] = mrr_list
    df_valid[f"Hit@{top_k}"] = hit_list
    df_valid[f"NDCG@{top_k}"] = ndcg_list

    if not output_path:
        base = os.path.basename(input_path)
        output_path = os.path.join(os.path.dirname(input_path), f"scored_{base}")

    df_valid.to_excel(output_path, index=False)

    print("\n========== RESULT ==========")
    print(f"Total rows       : {len(df)}")
    print(f"Valid queries    : {len(valid_indices)}")
    print(f"Missing query_id : {debug_missing_qid}")
    print(f"No relevant      : {debug_no_relevant}")
    print(f"Retrieval miss   : {debug_retrieval_miss}")
    print(f"MRR@{top_k}          : {mrr_mean:.6f}")
    print(f"Hit@{top_k}          : {hit_mean:.6f}")
    print(f"NDCG@{top_k}         : {ndcg_mean:.6f}")
    print(f"💾 Saved         : {output_path}")
    print("============================\n")

    return output_path


# =========================
# RUN
# =========================
if __name__ == "__main__":
    script_dir = Path(__file__).resolve().parent
    project_dir = script_dir.parent

    parser = argparse.ArgumentParser(description="MS MARCO Evaluation (Final Clean Version)")

    parser.add_argument("--input", default=str(script_dir / "eval_data_ms_marco.xlsx"))
    parser.add_argument("--qrels", default=str(project_dir / "qrels.json"))
    parser.add_argument("--output", default=None)
    parser.add_argument("--k", type=int, default=10)

    args = parser.parse_args()

    evaluate(
        input_path=args.input,
        qrels_path=args.qrels,
        output_path=args.output,
        top_k=args.k,
    )