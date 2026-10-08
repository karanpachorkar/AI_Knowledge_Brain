# ADR-007: Multi-Tenancy Architectural Enforcement

## Status
Accepted

## Context
Enterprise applications serving distinct organizations, business units, or customer tenants must guarantee strict data separation and zero cross-tenant data leakage across all system tiers.

## Decision
Enforce `tenant_id` mandatory scoping across all data stores:
- Database schema: Foreign keys and mandatory index columns on `tenant_id`.
- Vector search: Pre-filtered `tenant_id` payload match clause on every Qdrant query.
- Full-text search: OpenSearch query terms containing exact `tenant_id`.
- Object storage: MinIO bucket paths prefixed with `tenant_id`.
- Middleware: JWT validation injects `tenant_id` into request context.

## Consequences
### Positive
- Strict security barrier preventing multi-tenant data bleed.
### Negative
- All queries and repository methods must incorporate tenant scoping.
