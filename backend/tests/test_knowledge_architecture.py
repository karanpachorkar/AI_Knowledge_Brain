import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_knowledge_architecture_lifecycle(async_client: AsyncClient):
    # 1. Onboard Tenant and Login Admin
    reg_payload = {
        "tenant_name": "Knowledge Enterprise Inc",
        "tenant_slug": "knowledge-ent",
        "admin_email": "admin@knowledge-ent.com",
        "admin_password": "KnowledgePassword123!"
    }
    reg_res = await async_client.post("/api/v1/auth/register", json=reg_payload)
    assert reg_res.status_code == 201

    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "admin@knowledge-ent.com", "password": "KnowledgePassword123!", "tenant_slug": "knowledge-ent"}
    )
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Create Workspace
    ws_payload = {
        "name": "Engineering Workspace",
        "slug": "engineering",
        "description": "Engineering machine & SOP documentation"
    }
    ws_res = await async_client.post("/api/v1/workspaces", json=ws_payload, headers=headers)
    assert ws_res.status_code == 201
    ws_data = ws_res.json()
    assert ws_data["slug"] == "engineering"
    workspace_id = ws_data["id"]

    # 3. Create Knowledge Base within Workspace
    kb_payload = {
        "workspace_id": workspace_id,
        "name": "Machine Manuals KB",
        "slug": "machine-manuals",
        "description": "All machine operation manuals",
        "embedding_model": "bge-m3",
        "chunk_size": 512,
        "chunk_overlap": 64
    }
    kb_res = await async_client.post("/api/v1/knowledge-bases", json=kb_payload, headers=headers)
    assert kb_res.status_code == 201
    kb_data = kb_res.json()
    assert kb_data["slug"] == "machine-manuals"
    kb_id = kb_data["id"]

    # 4. List Document Types (Verifies Default Seeding)
    dt_res = await async_client.get("/api/v1/document-types", headers=headers)
    assert dt_res.status_code == 200
    doc_types = dt_res.json()
    assert len(doc_types) >= 5
    sop_type_id = doc_types[0]["id"]

    # 5. Create Document Record
    doc_payload = {
        "workspace_id": workspace_id,
        "knowledge_base_id": kb_id,
        "document_type_id": sop_type_id,
        "title": "Machine Cleaning Standard Operating Procedure",
        "description": "Standard cleaning procedures for production batching machines"
    }
    doc_res = await async_client.post("/api/v1/documents", json=doc_payload, headers=headers)
    assert doc_res.status_code == 201
    doc_data = doc_res.json()
    assert doc_data["title"] == "Machine Cleaning Standard Operating Procedure"
    doc_id = doc_data["id"]

    # 6. Add Version 1.0 to Document
    ver1_payload = {
        "file_name": "SOP_Cleaning_v1.pdf",
        "file_size": 1024500,
        "mime_type": "application/pdf",
        "checksum": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "storage_key": "knowledge-ent/engineering/sop_cleaning_v1.pdf",
        "metadata_json": {"author": "QA Department", "effective_date": "2026-01-01"}
    }
    ver1_res = await async_client.post(f"/api/v1/documents/{doc_id}/versions", json=ver1_payload, headers=headers)
    assert ver1_res.status_code == 201
    ver1_data = ver1_res.json()
    assert ver1_data["version_number"] == 1
    assert ver1_data["file_name"] == "SOP_Cleaning_v1.pdf"

    # 7. Add Version 2.0 to Document
    ver2_payload = {
        "file_name": "SOP_Cleaning_v2.pdf",
        "file_size": 1150000,
        "mime_type": "application/pdf",
        "checksum": "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",
        "storage_key": "knowledge-ent/engineering/sop_cleaning_v2.pdf",
        "metadata_json": {"author": "QA Department", "effective_date": "2026-10-01"}
    }
    ver2_res = await async_client.post(f"/api/v1/documents/{doc_id}/versions", json=ver2_payload, headers=headers)
    assert ver2_res.status_code == 201
    ver2_data = ver2_res.json()
    assert ver2_data["version_number"] == 2
