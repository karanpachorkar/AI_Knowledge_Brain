import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_grounded_rag_chat_completion_and_citations(async_client: AsyncClient):
    # 1. Register Tenant & Login
    reg = await async_client.post("/api/v1/auth/register", json={
        "tenant_name": "RAG Tenant 1",
        "tenant_slug": "rag-tenant-1",
        "admin_email": "admin@rag-tenant1.com",
        "admin_password": "RagPassword123!"
    })
    assert reg.status_code == 201

    login = await async_client.post("/api/v1/auth/login", json={
        "email": "admin@rag-tenant1.com",
        "password": "RagPassword123!",
        "tenant_slug": "rag-tenant-1"
    })
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Create Workspace and KB
    ws = await async_client.post("/api/v1/workspaces", json={"name": "RAG WS", "slug": "rag-ws"}, headers=headers)
    ws_id = ws.json()["id"]

    kb = await async_client.post("/api/v1/knowledge-bases", json={
        "workspace_id": ws_id,
        "name": "RAG KB",
        "slug": "rag-kb"
    }, headers=headers)
    kb_id = kb.json()["id"]

    # 3. Upload Document to Index
    doc_content = b"# Hydraulic Maintenance\nError ERR-505 indicates hydraulic pump overheating. Flush fluid reservoir and replace thermal valve."
    files = {"file": ("hydraulic_manual.txt", doc_content, "text/plain")}
    data = {
        "workspace_id": ws_id,
        "knowledge_base_id": kb_id,
        "title": "Hydraulic Maintenance Manual"
    }

    upload_res = await async_client.post("/api/v1/documents/upload", data=data, files=files, headers=headers)
    assert upload_res.status_code == 201
    doc_id = upload_res.json()["id"]

    # 4. Grounded Chat Query
    chat_req = {
        "workspace_id": ws_id,
        "knowledge_base_id": kb_id,
        "message": "How do I fix error ERR-505 on hydraulic pump?",
        "strict_grounding": True
    }

    chat_res = await async_client.post("/api/v1/chat", json=chat_req, headers=headers)
    assert chat_res.status_code == 200
    chat_data = chat_res.json()

    assert chat_data["is_grounded"] is True
    assert "ERR-505" in chat_data["answer"] or "Hydraulic" in chat_data["answer"]
    assert len(chat_data["citations"]) >= 1
    assert chat_data["citations"][0]["document_id"] == doc_id
    assert chat_data["citations"][0]["document_title"] in ["Hydraulic Maintenance Manual", "hydraulic_manual.txt"]

    # 5. Verify Conversation History Retrieval
    conv_id = chat_data["conversation_id"]
    convs_res = await async_client.get(f"/api/v1/chat/conversations?workspace_id={ws_id}", headers=headers)
    assert convs_res.status_code == 200
    convs_data = convs_res.json()
    assert len(convs_data) >= 1

    detail_res = await async_client.get(f"/api/v1/chat/conversations/{conv_id}", headers=headers)
    assert detail_res.status_code == 200
    detail_data = detail_res.json()
    assert detail_data["id"] == conv_id
    assert len(detail_data["messages"]) >= 2  # user + assistant


@pytest.mark.asyncio
async def test_ungrounded_rag_refusal_guardrails(async_client: AsyncClient):
    # 1. Register Tenant & Login
    reg = await async_client.post("/api/v1/auth/register", json={
        "tenant_name": "RAG Tenant 2",
        "tenant_slug": "rag-tenant-2",
        "admin_email": "admin@rag-tenant2.com",
        "admin_password": "RagPassword123!"
    })
    assert reg.status_code == 201

    login = await async_client.post("/api/v1/auth/login", json={
        "email": "admin@rag-tenant2.com",
        "password": "RagPassword123!",
        "tenant_slug": "rag-tenant-2"
    })
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    ws = await async_client.post("/api/v1/workspaces", json={"name": "Refusal WS", "slug": "refusal-ws"}, headers=headers)
    ws_id = ws.json()["id"]

    # 2. Ask completely ungrounded query
    chat_req = {
        "workspace_id": ws_id,
        "message": "What is the recipe for baking a chocolate brownie?",
        "strict_grounding": True
    }

    chat_res = await async_client.post("/api/v1/chat", json=chat_req, headers=headers)
    assert chat_res.status_code == 200
    chat_data = chat_res.json()

    assert chat_data["is_grounded"] is False
    assert "not have sufficient relevant information" in chat_data["answer"]
    assert len(chat_data["citations"]) == 0


@pytest.mark.asyncio
async def test_sse_streaming_chat_endpoint(async_client: AsyncClient):
    # 1. Register Tenant & Login
    reg = await async_client.post("/api/v1/auth/register", json={
        "tenant_name": "RAG Tenant 3",
        "tenant_slug": "rag-tenant-3",
        "admin_email": "admin@rag-tenant3.com",
        "admin_password": "RagPassword123!"
    })
    assert reg.status_code == 201

    login = await async_client.post("/api/v1/auth/login", json={
        "email": "admin@rag-tenant3.com",
        "password": "RagPassword123!",
        "tenant_slug": "rag-tenant-3"
    })
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    ws = await async_client.post("/api/v1/workspaces", json={"name": "Stream WS", "slug": "stream-ws"}, headers=headers)
    ws_id = ws.json()["id"]

    # 2. SSE Streaming request
    chat_req = {
        "workspace_id": ws_id,
        "message": "Explain ERR-505 overheating resolution",
        "strict_grounding": True
    }

    stream_res = await async_client.post("/api/v1/chat/stream", json=chat_req, headers=headers)
    assert stream_res.status_code == 200
    assert "text/event-stream" in stream_res.headers["content-type"]
    body_text = stream_res.text
    assert "data:" in body_text
    assert '"type": "done"' in body_text or '"type":"done"' in body_text
