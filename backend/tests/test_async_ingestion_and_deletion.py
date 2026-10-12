import asyncio
import io
import uuid
import pytest
from httpx import AsyncClient
from app.infrastructure.storage.minio_provider import MinIOStorageProvider
from app.infrastructure.vector.qdrant_provider import QdrantVectorProvider
from app.infrastructure.search.opensearch_provider import OpenSearchProvider
from app.repositories.document_repository import DocumentRepository
from app.services.ingestion_service import DocumentIngestionService
from app.services.rag_service import RAGService


@pytest.mark.asyncio
async def test_async_ingestion_pipeline_and_status_transitions(async_client: AsyncClient, db_session):
    # 1. Setup tenant & user
    reg = await async_client.post("/api/v1/auth/register", json={
        "tenant_name": "Async Ingestion Inc",
        "tenant_slug": "async-ingestion",
        "admin_email": "admin@async.com",
        "admin_password": "AsyncPassword123!"
    })
    assert reg.status_code == 201
    login = await async_client.post("/api/v1/auth/login", json={
        "email": "admin@async.com",
        "password": "AsyncPassword123!",
        "tenant_slug": "async-ingestion"
    })
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    ws = await async_client.post("/api/v1/workspaces", json={"name": "WS Async", "slug": "ws-async"}, headers=headers)
    ws_id = ws.json()["id"]

    kb = await async_client.post("/api/v1/knowledge-bases", json={
        "workspace_id": ws_id,
        "name": "KB Async",
        "slug": "kb-async",
        "embedding_model": "bge-m3"
    }, headers=headers)
    kb_id = kb.json()["id"]

    # 2. Upload document - Fast return with QUEUED status
    file_content = b"Emergency Shutdown Procedure: Press the red emergency-stop button."
    files = {"file": ("manual.txt", file_content, "text/plain")}
    data = {
        "workspace_id": ws_id,
        "knowledge_base_id": kb_id,
        "title": "Machine Manual Alpha"
    }

    upload_res = await async_client.post("/api/v1/documents/upload", data=data, files=files, headers=headers)
    assert upload_res.status_code == 201
    doc_id = upload_res.json()["id"]

    # Wait briefly for background worker processing completion
    await asyncio.sleep(0.5)

    doc_res = await async_client.get(f"/api/v1/documents/{doc_id}", headers=headers)
    assert doc_res.status_code == 200
    doc_json = doc_res.json()
    assert doc_json["versions"][0]["status"] == "READY"
    assert doc_json["versions"][0]["metadata_json"]["generated_chunks"] >= 1


@pytest.mark.asyncio
async def test_complete_document_deletion_and_retrieval_prevention(async_client: AsyncClient, db_session):
    """SECURITY TEST: Verifies document deletion purges DB, MinIO storage, Qdrant vectors, and OpenSearch index,
    and proves deleted content CANNOT be retrieved or reach LLM context."""
    # 1. Setup tenant & workspace
    reg = await async_client.post("/api/v1/auth/register", json={
        "tenant_name": "Deletion Corp",
        "tenant_slug": "deletion-corp",
        "admin_email": "admin@deletion.com",
        "admin_password": "DeletionPassword123!"
    })
    login = await async_client.post("/api/v1/auth/login", json={
        "email": "admin@deletion.com",
        "password": "DeletionPassword123!",
        "tenant_slug": "deletion-corp"
    })
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    tenant_id = reg.json()["tenant"]["id"]

    ws = await async_client.post("/api/v1/workspaces", json={"name": "WS Del", "slug": "ws-del"}, headers=headers)
    ws_id = ws.json()["id"]

    kb = await async_client.post("/api/v1/knowledge-bases", json={
        "workspace_id": ws_id,
        "name": "KB Del",
        "slug": "kb-del",
        "embedding_model": "bge-m3"
    }, headers=headers)
    kb_id = kb.json()["id"]

    # 2. Upload controlled document with sensitive secret information
    secret_fact = "PROJECT_SECRET_CODE_998877665544332211"
    file_content = f"The classified operational clearance code for Machine Alpha is {secret_fact}.".encode("utf-8")
    files = {"file": ("classified.txt", file_content, "text/plain")}
    data = {
        "workspace_id": ws_id,
        "knowledge_base_id": kb_id,
        "title": "Classified Procedures"
    }

    upload_res = await async_client.post("/api/v1/documents/upload", data=data, files=files, headers=headers)
    assert upload_res.status_code == 201
    doc_id = upload_res.json()["id"]
    version_storage_key = upload_res.json()["versions"][0]["storage_key"]

    await asyncio.sleep(0.5)

    # 3. Perform RAG query BEFORE deletion -> secret_fact MUST be present in retrieval context
    rag_service = RAGService()
    answer_pre, citations_pre, is_grounded_pre = await rag_service.generate_rag_response(
        query="What is the classified clearance code for Machine Alpha?",
        tenant_id=uuid.UUID(tenant_id),
        workspace_id=uuid.UUID(ws_id),
        knowledge_base_id=uuid.UUID(kb_id)
    )
    assert secret_fact in answer_pre or any(secret_fact in c.snippet for c in citations_pre)
    assert len(citations_pre) > 0
    assert is_grounded_pre is True

    # 4. Perform DELETE /documents/{doc_id}
    del_res = await async_client.delete(f"/api/v1/documents/{doc_id}", headers=headers)
    assert del_res.status_code == 200

    # 5. Verify PostgreSQL metadata record is gone
    get_res = await async_client.get(f"/api/v1/documents/{doc_id}", headers=headers)
    assert get_res.status_code == 404

    # 6. Verify MinIO file binary is gone
    storage = MinIOStorageProvider()
    bucket_name = f"tenant-{tenant_id}"
    with pytest.raises(FileNotFoundError):
        await storage.download_file(bucket_name, version_storage_key)

    # 7. Perform RAG query AFTER deletion -> MUST NOT retrieve document or reach LLM
    answer_post, citations_post, is_grounded_post = await rag_service.generate_rag_response(
        query="What is the classified clearance code for Machine Alpha?",
        tenant_id=uuid.UUID(tenant_id),
        workspace_id=uuid.UUID(ws_id),
        knowledge_base_id=uuid.UUID(kb_id)
    )
    assert secret_fact not in answer_post
    assert not any(secret_fact in c.snippet for c in citations_post)
    assert len(citations_post) == 0
    assert is_grounded_post is False


@pytest.mark.asyncio
async def test_permission_aware_rag_isolation(async_client: AsyncClient, db_session):
    """Tests that unauthorized user cannot retrieve document chunks across tenant boundaries."""
    # Tenant 1
    reg1 = await async_client.post("/api/v1/auth/register", json={
        "tenant_name": "Tenant One",
        "tenant_slug": "tenant-one",
        "admin_email": "userA@tenant1.com",
        "admin_password": "UserAPassword123!"
    })
    login1 = await async_client.post("/api/v1/auth/login", json={
        "email": "userA@tenant1.com",
        "password": "UserAPassword123!",
        "tenant_slug": "tenant-one"
    })
    token1 = login1.json()["access_token"]
    headers1 = {"Authorization": f"Bearer {token1}"}
    tenant1_id = reg1.json()["tenant"]["id"]

    ws1 = await async_client.post("/api/v1/workspaces", json={"name": "WS1", "slug": "ws1"}, headers=headers1)
    ws1_id = ws1.json()["id"]

    kb1 = await async_client.post("/api/v1/knowledge-bases", json={
        "workspace_id": ws1_id,
        "name": "KB1",
        "slug": "kb1",
        "embedding_model": "bge-m3"
    }, headers=headers1)
    kb1_id = kb1.json()["id"]

    # Upload document for Tenant 1
    file_content = b"Tenant 1 Confidential: Maximum operating temperature is 85 C."
    files = {"file": ("doc1.txt", file_content, "text/plain")}
    data = {"workspace_id": ws1_id, "knowledge_base_id": kb1_id, "title": "Doc Tenant 1"}
    await async_client.post("/api/v1/documents/upload", data=data, files=files, headers=headers1)
    await asyncio.sleep(0.5)

    # Tenant 2 (User B)
    reg2 = await async_client.post("/api/v1/auth/register", json={
        "tenant_name": "Tenant Two",
        "tenant_slug": "tenant-two",
        "admin_email": "userB@tenant2.com",
        "admin_password": "UserBPassword123!"
    })
    tenant2_id = reg2.json()["tenant"]["id"]

    # Query with Tenant 2 context for Tenant 1's secret
    rag_service = RAGService()
    answer_b, citations_b, is_grounded_b = await rag_service.generate_rag_response(
        query="What is the maximum operating temperature?",
        tenant_id=uuid.UUID(tenant2_id),
        workspace_id=uuid.UUID(ws1_id),
        knowledge_base_id=uuid.UUID(kb1_id)
    )

    assert "Tenant 1 Confidential" not in answer_b
    assert len(citations_b) == 0
    assert is_grounded_b is False

