# ERC-RAG

**Energy-based Retrieval Clustering for Retrieval-Augmented Generation** is a research implementation for Vietnamese economic question answering. It tests whether selecting a cluster of candidate passages with energy distance can improve RAG context selection over standard cosine retrieval.

> The reported evaluation uses automatically generated questions and should be treated as preliminary. See [Evaluation](#evaluation) before interpreting the reported metrics.

**Stack:** Python · multilingual-E5 · ChromaDB · K-Means · energy distance · LangChain

**Vietnamese overview:** [README.vi.md](README.vi.md) · **Application and pipeline:** [Folder_All/README.md](Folder_All/README.md)

## Method

1. Embed the question and retrieve 40 candidate passages from ChromaDB.
2. Cluster candidate passage vectors with K-Means and select the cluster count using silhouette score.
3. Calculate energy distance between the question vector and each cluster.
4. Pass the selected cluster to the downstream relevance and answer-generation stages.

The implementation is in `Folder_All/ingestion/single_vector_retriever.py`; the energy-distance function is in `Folder_All/ingestion/energy_base_distance.py`.

## Evaluation

The project report evaluates ERC-RAG on 1,000 automatically generated VNEIQAD question-answer pairs over 120,165 VEID chunks. It reports **MRR 0.62**, **NDCG@5 0.83**, **ROUGE-2 F1 0.68**, and **BLEU-2 0.65**, with GPT-5.0 mini used for answer generation. These are reported project results and have not yet been reproduced from the raw outputs in this repository.

The report also gives answer-generation comparisons against an earlier group system: BLEU-2 **0.61 → 0.65** and ROUGE-2 F1 **0.49 → 0.68**. The earlier system used GPT-4o-mini while the ERC-RAG run used GPT-5.0 mini, so the comparison is not controlled for the generation model.

## Data and reproducibility

The research uses the Vietnamese Economy Information Database (VEID) and VNEIQAD question set. The local index contains 120,165 chunks. The source corpus, question workbook, and vector database are not bundled here; provide them locally before running evaluation. Keep data with distribution restrictions outside Git.

For the full web application, API, and deployment instructions, see [Folder_All/README.md](Folder_All/README.md).

## Limitations

- The reported ERC-RAG metrics have not yet been reproduced from raw outputs in this repository.
- VNEIQAD questions were automatically generated, not independently curated; treat the results as preliminary until evaluated on manually reviewed, held-out questions.
- Retrieval metrics do not measure answer faithfulness or factual accuracy.
- NDCG uses the project's lexical-overlap relevance heuristic.
- The answer-generation comparison uses different LLMs: GPT-5.0 mini for ERC-RAG and GPT-4o-mini for the earlier group system.
- Energy distance between a single question vector and a candidate cluster is a research hypothesis; the benchmark should establish whether it helps on a controlled held-out set.
- No license is specified. Confirm rights to the source corpus and code before reuse.
