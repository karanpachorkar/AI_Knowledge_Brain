# ADR-005: MinIO for S3-Compatible Object Storage

## Status
Accepted

## Context
Raw uploaded files (PDFs, DOCX, scanned images, schematics) must be stored reliably without bloating the relational database or locking the platform into a specific cloud vendor's storage protocol.

## Decision
Use **MinIO** as an on-premise S3-compatible object storage server.
- Interfaced via standardized S3 SDK abstractions so that cloud deployments can seamlessly switch to AWS S3, Azure Blob Storage, or Google Cloud Storage via configuration changes.

## Consequences
### Positive
- Fully S3 API compatible.
- Works offline in air-gapped on-premise deployments.
### Negative
- Requires storage disk volume management.
