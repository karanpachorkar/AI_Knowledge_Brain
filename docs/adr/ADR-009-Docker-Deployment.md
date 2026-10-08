# ADR-009: Docker Compose as Primary On-Premise Deployment Engine

## Status
Accepted

## Context
Initial production targets involve single-server or PC on-premise Windows/Linux deployments accessible over internal LAN.

## Decision
Use **Docker Compose** as the primary container orchestration engine for V1.
- Provides isolated execution for Frontend, Backend, Worker, PostgreSQL, Redis, Qdrant, OpenSearch, MinIO, and Ollama.
- Configured with persistent volumes and health dependencies.
- Business logic is completely container-agnostic for future Kubernetes deployment.

## Consequences
### Positive
- Single command execution (`docker compose up -d`).
- Low operational complexity.
### Negative
- Single host hardware constraint.
