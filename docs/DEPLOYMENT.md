# Production Deployment Guide — Enterprise AI Knowledge Platform

This guide outlines step-by-step procedures for deploying the Enterprise AI Knowledge Platform on on-premise Windows/Linux servers using Docker Compose or Kubernetes cluster infrastructure.

---

## 1. Prerequisites

- **OS**: Windows Server 2022 / Windows 11 Pro or Linux (Ubuntu 22.04 LTS / RHEL 9)
- **Docker**: Docker Desktop or Docker Engine v24.0+ with Docker Compose v2.20+
- **Hardware Requirements**:
  - Minimum: 8 vCPUs, 16 GB RAM, 100 GB SSD storage
  - Recommended (Local Ollama LLM execution): 16 vCPUs, 32 GB RAM, NVIDIA GPU (8GB+ VRAM)

---

## 2. Environment Configuration

Create a `.env` file in the project root:

```env
APPLICATION_ENV=production
APPLICATION_HOST=0.0.0.0
APPLICATION_PORT=8000
SECRET_KEY=prod-secret-key-replace-with-secure-random-token
JWT_SECRET=prod-jwt-secret-replace-with-secure-random-token
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

POSTGRES_SERVER=postgres
POSTGRES_PORT=5432
POSTGRES_USER=app_user
POSTGRES_PASSWORD=secure_prod_password_here
POSTGRES_DB=enterprise_ai_db

REDIS_HOST=redis
REDIS_PORT=6379
QDRANT_URL=http://qdrant:6333
OPENSEARCH_URL=http://opensearch:9200
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=minio_admin_key
MINIO_SECRET_KEY=minio_admin_secret
MINIO_SECURE=false

OLLAMA_BASE_URL=http://ollama:11434
CHAT_MODEL=qwen2.5:7b
EMBEDDING_MODEL=bge-m3
RERANKER_MODEL=bge-reranker-large
VISION_MODEL=qwen2-vl:7b

LOG_LEVEL=INFO
LOG_FORMAT=json
```

---

## 3. Starting the Production Stack

Execute the following commands to initialize database migrations and bring up all micro-services:

```bash
# 1. Pull required container images and build services
docker compose build --no-cache

# 2. Start core database and infrastructure services
docker compose up -d postgres redis qdrant opensearch minio ollama

# 3. Apply database migrations
docker compose run --rm backend alembic upgrade head

# 4. Start backend API worker and Next.js frontend
docker compose up -d backend worker frontend
```

---

## 4. Pulling Production AI Models in Ollama

Once Ollama container is running:

```bash
docker exec -it enterprise_ai_ollama ollama pull qwen2.5:7b
docker exec -it enterprise_ai_ollama ollama pull bge-m3
docker exec -it enterprise_ai_ollama ollama pull qwen2-vl:7b
```

---

## 5. Health & Verification Probes

- **Backend API Docs**: `http://localhost:8000/docs`
- **Health Probe**: `http://localhost:8000/health`
- **Readiness Probe**: `http://localhost:8000/readiness`
- **Frontend Workspace**: `http://localhost:3000`
