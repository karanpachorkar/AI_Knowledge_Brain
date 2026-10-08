# ADR-010: Application-Level Authentication with Argon2id Hashing

## Status
Accepted

## Context
The platform must support self-contained user management and authentication without mandatory external identity provider dependencies, while supporting enterprise extension points for SSO in future iterations.

## Decision
Implement **Application-Level Authentication**:
- Argon2id password hashing algorithm.
- Short-lived JWT access tokens and long-lived refresh tokens stored securely.
- Strict separation between Authentication (identity verification) and Authorization (RBAC permissions).

## Consequences
### Positive
- Air-gapped independence from cloud identity providers.
- Modern cryptographically secure password storage.
### Negative
- Application assumes responsibility for password policy enforcement and resets.
