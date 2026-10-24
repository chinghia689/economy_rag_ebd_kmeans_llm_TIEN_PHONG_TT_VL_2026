# ERC-RAG

**Energy-based Retrieval Clustering for Retrieval-Augmented Generation** is a research implementation for Vietnamese economic question answering. It tests whether selecting a cluster of candidate passages with energy distance can improve RAG context selection over standard cosine retrieval.

> The current benchmark check does not establish that ERC-RAG outperforms the cosine baseline. See [Evaluation](#evaluation) before interpreting the reported metrics.

**Stack:** Python · multilingual-E5 · ChromaDB · K-Means · energy distance · LangChain

**Vietnamese overview:** [README.vi.md](README.vi.md) · **Application and pipeline:** [Folder_All/README.md](Folder_All/README.md)

## Method

1. Embed the question and retrieve 40 candidate passages from ChromaDB.
2. Cluster candidate passage vectors with K-Means and select the cluster count using silhouette score.
3. Calculate energy distance between the question vector and each cluster.
4. Pass the selected cluster to the downstream relevance and answer-generation stages.

The implementation is in `Folder_All/ingestion/single_vector_retriever.py`; the energy-distance function is in `Folder_All/ingestion/energy_base_distance.py`.

## Evaluation

An initial pure multilingual-E5 cosine top-5 run on the existing 1,000-question workbook and Chroma index produced:

| Metric | Cosine top-5 |
| --- | ---: |
| MRR | 0.7352 |
| Hit@5 | 0.8040 |
| NDCG@5 | 0.9805 |

The current project materials report ERC-RAG **MRR 0.62** and **NDCG@5 0.83**. The existing ERC figures have not yet been reproduced through the same raw retrieval outputs and confirmed identical settings, so this is a preliminary comparison—not evidence that either method wins. The baseline is higher on these reported values; do not claim an ERC improvement until both methods are rerun with the same questions, index, and metric implementation.

The baseline uses the project's current metric functions: MRR and Hit@5 look for the exact ground-truth answer text inside retrieved chunks, while NDCG@5 uses lexical token overlap. These definitions should be interpreted as project-specific retrieval proxies, not answer-quality metrics.

### Reproduce the cosine baseline

The question workbook and vector index are not committed. Supply the local paths to the benchmark workbook and Chroma index:

```bash
cd Folder_All
python scoring/baseline_cosine.py \
  --input "/path/to/file 1000 cau hoi.xlsx" \
  --vector-store "/path/to/chroma_economy_db"
```

The script prints MRR, Hit@5, NDCG@5, and elapsed time; it does not write an output workbook. The `query:` prefix required by multilingual-E5 is applied in batches.

## Data and reproducibility

The research uses the Vietnamese Economy Information Database (VEID) and VNEIQAD question set. The local index contains 120,165 chunks. The source corpus, question workbook, and vector database are not bundled here; provide them locally before running evaluation. Keep data with distribution restrictions outside Git.

For the full web application, API, and deployment instructions, see [Folder_All/README.md](Folder_All/README.md).

## Limitations

- The baseline and ERC-RAG numbers need a matched rerun before making a comparative claim.
- Retrieval metrics do not measure answer faithfulness or factual accuracy.
- NDCG uses the project's lexical-overlap relevance heuristic.
- Energy distance between a single question vector and a candidate cluster is a research hypothesis; the benchmark should establish whether it helps on a controlled held-out set.
- No license is specified. Confirm rights to the source corpus and code before reuse.
