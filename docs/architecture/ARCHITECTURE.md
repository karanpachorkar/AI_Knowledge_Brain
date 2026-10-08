# Enterprise AI Knowledge Platform — System Architecture Document

## Executive Overview
The **Enterprise AI Knowledge Platform** is a production-grade, generic enterprise solution for knowledge management, permissions-enforced Retrieval-Augmented Generation (RAG), and local/cloud AI model orchestration. 

It is designed to be deployed on-premise (e.g. Docker Desktop/Engine on Windows Server or Linux) or scaled into hybrid cloud environments without changing application logic or architectural contracts.

---

## Key Architectural Principles

1. **Strict Multi-Tenancy & Data Isolation**: Tenant boundaries are enforced across all persistence, vector indexing, full-text search, storage, and background processing layers.
2. **Permission-Aware RAG Security**: Unauthorized chunks are filtered out before reaching any LLM prompt context construction.
3. **AI Model Gateway & Provider Abstraction**: Business logic is completely decoupled from model providers (Ollama, OpenAI, Anthropic, Gemini, vLLM).
4. **Modular Monolith**: Clean layered architecture (API -> Application -> Domain -> Infrastructure) with asynchronous background workers for high throughput without microservice complexity.
5. **Configuration-Driven Design**: Company names, document types, departments, roles, AI models, and vector models are stored as metadata rather than hardcoded.

---

## Logical Component Architecture

```text
                        ┌─────────────────────────────┐
                        │        Enterprise Users     │
                        │ Browser / Web Application   │
                        └──────────────┬──────────────┘
                                       │
                                       ▼
                        ┌─────────────────────────────┐
                        │       Web / API Layer       │
                        │      FastAPI Backend        │
                        └──────────────┬──────────────┘
                                       │
                 ┌─────────────────────┼─────────────────────┐
                 │                     │                     │
                 ▼                     ▼                     ▼
          Authentication        Authorization          API Layer
          & Sessions             & RBAC                  & Validation
                 │                     │
                 └──────────────┬──────┘
                                ▼
                    ┌─────────────────────────┐
                    │   Application Core      │
                    │                         │
                    │ Knowledge Management    │
                    │ Document Management     │
                    │ RAG Orchestration       │
                    │ Chat                    │
                    │ AI Model Gateway        │
                    │ Audit                   │
                    │ Administration          │
                    └───────────┬─────────────┘
                                │
          ┌─────────────────────┼─────────────────────┐
          │                     │                     │
          ▼                     ▼                     ▼
   PostgreSQL                Redis              Background Worker
   System of Record          Cache              Async Processing
          │                                         │
          │                                         ▼
          │                               Ingestion Pipeline
          │                                         │
          │                         ┌───────────────┼──────────────┐
          │                         ▼               ▼              ▼
          │                       Parser           OCR         Structure
          │                         │               │              │
          │                         └───────────────┼──────────────┘
          │                                         ▼
          │                                      Chunking
          │                                         │
          │                                         ▼
          │                                      Embedding
          │                                         │
          │                          ┌──────────────┴──────────────┐
          │                          ▼                             ▼
          │                       Qdrant                      OpenSearch
          │                     Vector Search                 BM25 Search
          │                          │                             │
          │                          └──────────────┬──────────────┘
          │                                         ▼
          │                                  Hybrid Retrieval
          │                                         │
          │                                         ▼
          │                                      Reranker
          │                                         │
          │                                         ▼
          │                                  Context Builder
          │                                         │
          │                                         ▼
          │                                   Model Gateway
          │                                         │
          │                                         ▼
          │                                Local / Cloud LLM
          │
          ▼
       MinIO
 Object Storage
```

---

## System Components

### 1. Web & Frontend Layer
- **Framework**: React / Next.js with TypeScript and Vanilla CSS token-driven styling.
- **Responsibilities**: Responsive Enterprise UI, Chat streaming, Document Management dashboard, Admin panel, Health indicators.

### 2. FastAPI Backend Monolith
- **Framework**: FastAPI (Python 3.11+) with Pydantic v2 and SQLAlchemy 2.0 (Async).
- **Responsibilities**: REST API routing, Session & JWT Auth, RBAC enforcement, Request validation, Business domain logic.

### 3. Asynchronous Worker Engine
- **Engine**: Celery / Async Python Background Workers with Redis queue.
- **Responsibilities**: Heavy document parsing (Docling), OCR (PaddleOCR/Tesseract), Chunking, Batch embedding generation, Indexing, Document deletion cascade.

### 4. Storage & Persistence Services
- **PostgreSQL 16**: System of record for users, tenants, roles, permissions, workspaces, knowledge bases, documents, versions, metadata, ACLs, conversations, messages, citations, audit logs.
- **Redis 7**: Cache layer, rate-limiting, job state management, SSE/Streaming synchronization.
- **Qdrant Vector DB**: HNSW vector storage supporting dense semantic retrieval filtered by tenant, workspace, KB, and user security scopes.
- **OpenSearch 2.13**: BM25 keyword search engine for part numbers, exact codes, error IDs, machine specifications.
- **MinIO**: S3-compatible object storage for original uploaded PDFs, Office docs, images, and parsed artifacts.
- **Ollama AI Server**: Local open-source LLM runtime (e.g. Qwen2.5) and embedding provider (BAAI BGE-M3).

---

## Data Model & Hierarchy

```text
Tenant
 └── Workspace
      └── Knowledge Base
           └── Document
                └── Document Version
                     └── Pages / Sections
                          └── Chunks
```

---

## Security & Permission Model
- **Authentication**: Modern password hashing with Argon2id, JWT access & refresh tokens.
- **Authorization**: Granular Role-Based Access Control (RBAC).
- **Permission-Aware Retrieval**: Document & Knowledge Base ACLs are resolved at query time. The search filter passed to Qdrant/OpenSearch restricts candidate vectors to only those document IDs the user has explicit permission to read.
