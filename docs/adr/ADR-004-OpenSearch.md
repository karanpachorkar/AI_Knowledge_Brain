# ADR-004: OpenSearch for BM25 Keyword Search

## Status
Accepted

## Context
Enterprise technical documents frequently contain part numbers, serial codes, machine IDs, exact error strings, and domain-specific acronyms that dense semantic embeddings may miss or retrieve with lower relevance scores.

## Decision
Use **OpenSearch** for BM25 full-text keyword retrieval alongside Qdrant vector retrieval.
- Enables hybrid retrieval (Dense Semantic + BM25 Full-Text) fused via Reciprocal Rank Fusion (RRF) and re-ranking.

## Consequences
### Positive
- High precision for exact technical IDs and codes.
### Negative
- Requires JVM memory resources in the Docker host stack.
