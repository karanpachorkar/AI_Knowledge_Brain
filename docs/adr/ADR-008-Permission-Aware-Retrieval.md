# ADR-008: Permission-Aware RAG Security

## Status
Accepted

## Context
Retrieval-Augmented Generation in enterprise environments must guarantee that unauthorized document content is never sent to the LLM context, preventing information disclosure attacks.

## Decision
Enforce **Permission-Aware Retrieval**:
1. Authenticate user and resolve active tenant and user ACL rights before vector search.
2. Formulate Qdrant and OpenSearch filters containing only accessible Knowledge Base IDs and Document IDs.
3. Retrieve candidate chunks from storage ONLY within authorized bounds.
4. Rerank and pass authorized chunks to prompt construction.
- Filtering after retrieval or filtering LLM output is strictly prohibited.

## Consequences
### Positive
- Zero risk of unauthorized content leaking into LLM generation prompts.
### Negative
- Query execution requires ACL pre-resolution.
