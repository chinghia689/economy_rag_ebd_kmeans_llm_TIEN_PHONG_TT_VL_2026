# MS MARCO Scoring Folder

This folder is dedicated to evaluating MS MARCO only.

## Files

- `export_ms_marco_eval.py`: export eval questions from MS MARCO with `query_id` and `relevant_doc_ids`.
- `create_eval_data.py`: run your chatbot on those questions and save answers + retrieved doc ids.
- `evaluate.py`: score retrieval by doc id with `Hit@k`, `MRR@k`, `NDCG@k` and save resolved ids.
- `metric/`: utility metrics currently used for scoring: `Hit@k`, `MRR`, `NDCG@k`.

## Typical workflow

1. Export eval set:

```bash
python scoring_ms_marco/export_ms_marco_eval.py --sample-size 1000 --output scoring_ms_marco/ms_marco_eval.xlsx
```

2. Generate chatbot outputs:

```bash
python scoring_ms_marco/create_eval_data.py --input scoring_ms_marco/ms_marco_eval.xlsx --output eval_data_ms_marco.xlsx --max 100 --vector-store ./chroma_ms_marco_db --llm openai
```

3. Score results:

```bash
python scoring_ms_marco/evaluate.py --input scoring_ms_marco/eval_data_ms_marco.xlsx --qrels qrels.json --queries queries.json --k 5
```

Output is saved as `ms_marco_scored_<input_filename>.xlsx` unless `--output` is provided.

## Metric utilities in metric/

Use these functions directly if you want extra scores on the generated eval file:

- `scoring_ms_marco.metric.hit_rate_excel`
- `scoring_ms_marco.metric.mrr_excel`
- `scoring_ms_marco.metric.ndcg_excel`

Example:

```bash
python -c "from scoring_ms_marco.metric import hit_rate_excel; hit_rate_excel('scoring_ms_marco/eval_data_ms_marco.xlsx', k=5)"
```
