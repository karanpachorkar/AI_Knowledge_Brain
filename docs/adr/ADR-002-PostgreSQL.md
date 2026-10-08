# ADR-002: PostgreSQL as Primary System of Record

## Status
Accepted

## Context
The platform requires robust transactional integrity, complex relational metadata modeling (tenants, workspaces, knowledge bases, document versions, permissions, audit logs), and SQL query performance.

## Decision
Use **PostgreSQL 16** as the primary relational database system of record.
- Managed using SQLAlchemy (Async engine) and Alembic for versioned schema migrations.
- File binaries are stored in MinIO, while relational metadata and foreign key relationships are strictly maintained in PostgreSQL.

## Consequences
### Positive
- Strong ACID compliance and battle-tested enterprise performance.
- Excellent async support via `asyncpg`.
### Negative
- Requires schema migration management via Alembic.
