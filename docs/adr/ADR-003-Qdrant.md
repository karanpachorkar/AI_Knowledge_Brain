# ADR-003: Qdrant as Vector Search Engine

## Status
Accepted

## Context
High-dimensional dense vector embeddings generated during document ingestion require efficient ANN (Approximate Nearest Neighbor) similarity search with strict payload filtering (tenant_id, document_id, ACL permissions).

## Decision
Use **Qdrant** as the dedicated vector database engine.
- High-performance HNSW index execution.
- Rich payload filtering applied natively at vector search execution time.

## Consequences
### Positive
- Sub-millisecond vector retrieval with exact pre-filtering capability.
- Standalone service easily run in Docker or Kubernetes.
### Negative
- Requires maintaining a separate vector index synchronized with primary metadata.
