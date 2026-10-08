import pytest
from httpx import AsyncClient
from app.domain.chunking.chunker import DocumentChunk
from app.services.indexing_service import IndexingService
from app.services.retrieval_service import RetrievalService


@pytest.mark.asyncio
async def test_indexing_and_hybrid_retrieval_service():
    indexing_service = IndexingService()
    retrieval_service = RetrievalService()

    tenant_id = "00000000-0000-0000-0000-000000000010"
    workspace_id = "00000000-0000-0000-0000-000000000020"
    kb_id = "00000000-0000-0000-0000-000000000030"

    chunks = [
        DocumentChunk(
            tenant_id=tenant_id,
            workspace_id=workspace_id,
            knowledge_base_id=kb_id,
            document_id="doc-1",
            document_version_id="ver-1",
            chunk_index=0,
            content="Section: Cleaning SOP\nPerform hydraulic fluid level check and daily machine cleaning procedure.",
            section_title="Cleaning SOP",
            page_number=1
        ),
        DocumentChunk(
            tenant_id=tenant_id,
            workspace_id=workspace_id,
            knowledge_base_id=kb_id,
            document_id="doc-2",
            document_version_id="ver-1",
            chunk_index=0,
            content="Section: Error Codes\nError Code ERR-404 indicates hydraulic pressure sensor failure.",
            section_title="Error Codes",
            page_number=3
        )
    ]

    # Index chunks
    indexed = await indexing_service.index_chunks(chunks)
    assert indexed is True

    # Search for exact technical code ERR-404
    results = await retrieval_service.hybrid_search(
        query="ERR-404 hydraulic pressure sensor",
        tenant_id=tenant_id,
        limit=5
    )

    assert len(results) >= 1
    assert "ERR-404" in results[0].content
    assert results[0].fused_score > 0.0


@pytest.mark.asyncio
async def test_permission_aware_search_api(async_client: AsyncClient):
    # 1. Onboard tenant and admin
    reg = await async_client.post("/api/v1/auth/register", json={
        "tenant_name": "Search Tenant",
        "tenant_slug": "search-tenant",
        "admin_email": "admin@search-tenant.com",
        "admin_password": "SearchPassword123!"
    })
    assert reg.status_code == 201

    login = await async_client.post("/api/v1/auth/login", json={
        "email": "admin@search-tenant.com",
        "password": "SearchPassword123!",
        "tenant_slug": "search-tenant"
    })
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Create Workspace and KB
    ws = await async_client.post("/api/v1/workspaces", json={"name": "Search WS", "slug": "search-ws"}, headers=headers)
    ws_id = ws.json()["id"]

    kb = await async_client.post("/api/v1/knowledge-bases", json={
        "workspace_id": ws_id,
        "name": "Search KB",
        "slug": "search-kb"
    }, headers=headers)
    kb_id = kb.json()["id"]

    # 3. Upload File to index
    file_content = b"# Calibration Guide\nCalibrate pressure sensors to 150 PSI before initial run."
    files = {"file": ("calibration.txt", file_content, "text/plain")}
    data = {
        "workspace_id": ws_id,
        "knowledge_base_id": kb_id,
        "title": "Calibration Guide SOP"
    }

    upload_res = await async_client.post("/api/v1/documents/upload", data=data, files=files, headers=headers)
    assert upload_res.status_code == 201

    # 4. Search API execution
    search_req = {
        "query": "PSI calibration pressure sensors",
        "workspace_id": ws_id,
        "knowledge_base_id": kb_id,
        "limit": 5
    }
    search_res = await async_client.post("/api/v1/search", json=search_req, headers=headers)
    assert search_res.status_code == 200
    search_data = search_res.json()
    assert search_data["query"] == "PSI calibration pressure sensors"
    assert search_data["total_results"] >= 1
    assert "PSI" in search_data["results"][0]["content"]
