import pytest
from httpx import AsyncClient
from app.repositories.audit_repository import AuditRepository


@pytest.mark.asyncio
async def test_request_id_middleware(async_client: AsyncClient):
    res = await async_client.get("/health")
    assert res.status_code == 200
    assert "x-request-id" in res.headers
    assert len(res.headers["x-request-id"]) > 0


@pytest.mark.asyncio
async def test_audit_log_creation_and_api(async_client: AsyncClient, db_session):
    # 1. Register Tenant & Login Admin
    reg = await async_client.post("/api/v1/auth/register", json={
        "tenant_name": "Audit Tenant",
        "tenant_slug": "audit-tenant",
        "admin_email": "admin@audit-tenant.com",
        "admin_password": "AuditPassword123!"
    })
    assert reg.status_code == 201

    login = await async_client.post("/api/v1/auth/login", json={
        "email": "admin@audit-tenant.com",
        "password": "AuditPassword123!",
        "tenant_slug": "audit-tenant"
    })
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Retrieve tenant ID from user profile or DB
    user_res = await async_client.get("/api/v1/auth/me", headers=headers)
    assert user_res.status_code == 200
    user_data = user_res.json()
    tenant_id = user_data["tenant_id"]

    # 2. Log Audit Event directly via AuditRepository
    audit_repo = AuditRepository(db_session)
    await audit_repo.log_event(
        tenant_id=tenant_id,
        user_id=user_data["id"],
        action="DOCUMENT_UPLOAD",
        resource_type="document",
        resource_id="doc-12345",
        ip_address="127.0.0.1",
        user_agent="TestRunner",
        metadata_json={"file_name": "sop_manual.pdf"}
    )
    await db_session.commit()

    # 3. Retrieve Audit Logs via API Endpoint
    audit_res = await async_client.get("/api/v1/audit-logs", headers=headers)
    assert audit_res.status_code == 200
    logs = audit_res.json()
    assert len(logs) >= 1
    assert logs[0]["action"] == "DOCUMENT_UPLOAD"
    assert logs[0]["resource_type"] == "document"
    assert logs[0]["resource_id"] == "doc-12345"
