import argparse
import pandas as pd
import json
import ir_datasets


def export_ms_marco_eval_ir(output_path="ms_marco_eval.xlsx", limit=500):
    print("🚀 Export MS MARCO IR eval...")

    dataset = ir_datasets.load("msmarco-passage/dev/small")
    docs_store = dataset.docs_store()

    rows = []

    queries = list(dataset.queries_iter())
    if limit:
        queries = queries[:limit]

    selected_query_ids = {str(query.query_id) for query in queries}
    qrels_map = {}

    # build qrels map
    for qrel in dataset.qrels_iter():
        qid = str(qrel.query_id)
        did = str(qrel.doc_id)

        if qid not in selected_query_ids:
            continue

        if qid not in qrels_map:
            qrels_map[qid] = []

        qrels_map[qid].append(did)

    # build rows
    for q in queries:
        qid = str(q.query_id)
        question = q.text

        relevant_doc_ids = qrels_map.get(qid, [])
        contexts_ground_truth = []
        for doc_id in relevant_doc_ids:
            doc = docs_store.get(doc_id)
            if doc is None:
                continue

            doc_text = str(getattr(doc, "text", "")).strip()
            if doc_text:
                contexts_ground_truth.append(doc_text)

        rows.append(
            {
                "query_id": qid,
                "question": question,
                "relevant_doc_ids": json.dumps(relevant_doc_ids),
                "contexts_ground_truth": json.dumps(contexts_ground_truth, ensure_ascii=False),
            }
        )

    df = pd.DataFrame(rows)
    df.to_excel(output_path, index=False)

    print(f"✅ Saved: {output_path}")
    print(f"Rows: {len(df)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export MS MARCO eval set with query_id and relevant_doc_ids")
    parser.add_argument("--output", type=str, default="scoring_ms_marco/ms_marco_eval.xlsx")
    parser.add_argument("--sample-size", type=int, default=500)
    args = parser.parse_args()

    export_ms_marco_eval_ir(output_path=args.output, limit=args.sample_size)