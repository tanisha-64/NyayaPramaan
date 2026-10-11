# RAG evaluation: land_dispute_v1 (sha 3ce5d775172a1d2c)

Retriever: `bm25-offline-baseline`, K=3, chunks=5, abstain threshold=0.34

## retrieval

| metric | value |
|---|---|
| recall@3 | 1.0 |
| hit@3 | 1.0 |
| mrr | 0.9444 |
| ndcg@3 | 0.9545 |

## abstention

| metric | value |
|---|---|
| correct_abstention_rate | 1.0 |
| hard_negative_abstention_rate | 0.5 |
| false_abstention_rate | 0.0 |
| accuracy | 1.0 |

## citations

| metric | value |
|---|---|
| good_answers_f1 | 1.0 |
| wrong_page_answers_precision | 0.0 |
| wrong_page_answers_invalid_rate | 0.5 |
| good_answers_invalid_rate | 0.0 |

## groundedness_proxy

| metric | value |
|---|---|
| good_answers | 1.0 |
| hallucinated_answers | 0.3333 |
| unsupported_claim_rate_hallucinated | 0.6667 |
| unsupported_claim_rate_good | 0.0 |

## hybrid

| metric | value |
|---|---|
| hybrid_recall@3 | 0.9722 |
| hybrid_hit@3 | 1.0 |
| hybrid_mrr | 0.8796 |
| hybrid_ndcg@3 | 0.8892 |
| semantic_only_recall@3 | 0.9722 |
| semantic_only_hit@3 | 1.0 |
| semantic_only_mrr | 0.8796 |
| semantic_only_ndcg@3 | 0.8892 |

## leakage

| metric | value |
|---|---|
| cross_case_chunk_rate | 0.0 |
| other_case_marker_hits | 0 |
| chunks_checked | 72 |

## failure_modes

| metric | value |
|---|---|
| rpc_unavailable_recall@3 | 0.9722 |
| rpc_unavailable_hit@3 | 1.0 |
| rpc_unavailable_mrr | 0.9074 |
| rpc_unavailable_ndcg@3 | 0.9097 |
| rpc_unavailable_cross_case_chunks | 0 |
| rpc_unavailable_questions | 18 |
| no_query_embedding_recall@3 | 1.0 |
| no_query_embedding_hit@3 | 1.0 |
| no_query_embedding_mrr | 0.9444 |
| no_query_embedding_ndcg@3 | 0.9545 |
| no_query_embedding_cross_case_chunks | 0 |
| no_query_embedding_questions | 18 |

## followups

| metric | value |
|---|---|
| followups | 4 |
| raw_recall@3 | 1.0 |
| rewritten_recall@3 | 1.0 |
| rewriter_gate_hit_rate | 1.0 |

## conflict

| metric | value |
|---|---|
| both_pages_recall@3 | 1.0 |
| questions | 2 |

## hybrid vs semantic-only by question category

| category | semantic-only recall | hybrid recall |
|---|---|---|
| fact | 1.0 | 1.0 |
| hinglish | 1.0 | 1.0 |
| multi-page | 0.75 | 0.75 |
| paraphrase | 1.0 | 1.0 |
| short | 1.0 | 1.0 |

> **Limits.** Hashed bag-of-words stub embeddings, one small fictional case: a regression gate for fusion and isolation code, not a measurement of real embedding quality.

## Answerable questions with no expected page in top-K

- none
