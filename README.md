# Enterprise AI Knowledge Platform

Production-grade, generic **Enterprise AI Knowledge Platform** featuring permissions-enforced Retrieval-Augmented Generation (RAG), multi-tenancy, document ingestion pipelines, and an AI Model Gateway.

> **Designed for On-Premise Windows/Linux deployment via Docker Compose or scaling to Enterprise Cloud environments.**

---

## 🏗 Key Features & Architecture

- **Generic Multi-Tenant Architecture**: Complete logical and physical isolation per tenant across relational data, vector embeddings, full-text indexes, and object storage.
- **Permission-Aware RAG**: ACL security pre-filtering guarantees that unauthorized document chunks are never exposed to the LLM prompt context.
- **AI Model Gateway**: Provider abstraction allowing capability-driven model routing across local runtimes (Ollama, vLLM) and cloud providers (OpenAI, Anthropic, Gemini) without altering business logic.
- **Hybrid Search**: Fuses dense vector retrieval (Qdrant) with BM25 full-text search (OpenSearch) and cross-encoder re-ranking for maximum accuracy on enterprise technical codes and exact terminology.
- **Asynchronous Ingestion Engine**: Worker pipeline performing document parsing, OCR, chunking, and embedding generation without blocking web requests.

---

## 📁 Repository Structure

```text
AI_Knowledge_Brain/
├── backend/
│   ├── app/
│   │   ├── api/             # FastAPI REST endpoints & routers
│   │   ├── core/            # Configuration, database engine, redis, logging
│   │   ├── domain/          # Pure domain models & business rules
│   │   ├── application/     # Application use cases & services
│   │   ├── infrastructure/  # External integrations (Qdrant, OpenSearch, MinIO, Ollama)
│   │   ├── models/          # SQLAlchemy ORM models
│   │   ├── schemas/         # Pydantic request & response schemas
│   │   ├── services/        # Service orchestration layer
│   │   ├── repositories/    # Data access abstraction
│   │   ├── workers/         # Asynchronous task worker entrypoints
│   │   └── main.py          # FastAPI application entrypoint
│   ├── alembic/             # Database migrations configuration
│   └── tests/               # Unit, integration, and security test suite
├── frontend/
│   ├── src/
│   │   └── app/             # Next.js App Router (Dashboard, KB, Chat, Admin)
│   ├── package.json
│   └── tsconfig.json
├── infrastructure/
│   └── docker/              # Production Multi-stage Dockerfiles
├── docs/
│   ├── architecture/        # Deep-dive architecture specs
│   └── adr/                 # Architecture Decision Records (ADR-001 to ADR-010)
├── docker-compose.yml       # Complete multi-service compose orchestration
├── .env.example             # Template environment configuration
├── .gitignore
└── README.md
```

---

## 🚀 Quick Start (Docker Compose Deployment)

### Prerequisites
- Docker Desktop or Docker Engine (v24.0+)
- Docker Compose (v2.20+)

### Setup Steps
1. Copy the template environment variables:
   ```bash
   cp .env.example .env
   ```
2. Launch the full enterprise stack:
   ```bash
   docker compose up -d
   ```
3. Access services:
   - **Frontend UI**: `http://localhost:3000`
   - **FastAPI OpenAPI Docs**: `http://localhost:8000/docs`
   - **Health Check Endpoint**: `http://localhost:8000/health`
   - **Readiness Probe**: `http://localhost:8000/readiness`

---

## 🧪 Testing

Run pytest within the backend environment:
```bash
cd backend
python -m pytest
```

---

## 📜 Architecture Decision Records (ADRs)

- [ADR-001: Modular Monolith Architecture](docs/adr/ADR-001-Modular-Monolith.md)
- [ADR-002: PostgreSQL as Primary System of Record](docs/adr/ADR-002-PostgreSQL.md)
- [ADR-003: Qdrant Vector Search Engine](docs/adr/ADR-003-Qdrant.md)
- [ADR-004: OpenSearch BM25 Keyword Search](docs/adr/ADR-004-OpenSearch.md)
- [ADR-005: MinIO S3 Object Storage](docs/adr/ADR-005-MinIO.md)
- [ADR-006: AI Model Gateway & Provider Abstraction](docs/adr/ADR-006-Model-Gateway.md)
- [ADR-007: Multi-Tenancy Architectural Enforcement](docs/adr/ADR-007-Multi-Tenancy.md)
- [ADR-008: Permission-Aware RAG Security](docs/adr/ADR-008-Permission-Aware-Retrieval.md)
- [ADR-009: Docker Compose On-Premise Engine](docs/adr/ADR-009-Docker-Deployment.md)
- [ADR-010: Application-Level Authentication](docs/adr/ADR-010-Application-Authentication.md)
