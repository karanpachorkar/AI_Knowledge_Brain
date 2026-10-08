import io
import pytest
from httpx import AsyncClient
from app.domain.chunking.chunker import DocumentChunker
from app.infrastructure.parsers.standard_parser import StandardDocumentParser
from app.services.file_validation_service import FileValidationService


@pytest.mark.asyncio
async def test_file_validation_service():
    # Valid text file
    content = b"This is a test document content for ingestion pipeline testing."
    file_stream = io.BytesIO(content)
    checksum, size = FileValidationService.calculate_checksum_and_validate(file_stream, "test.txt", "text/plain")

    assert len(checksum) == 64
    assert size == len(content)


@pytest.mark.asyncio
async def test_document_parser_and_chunker():
    sample_document = (
        "# Machine Safety Manual\n"
        "Ensure all emergency stop buttons are accessible before operation.\n\n"
        "# Maintenance Procedure\n"
        "Perform weekly lubrication on drive chains and verify hydraulic pressure."
    )
    parser = StandardDocumentParser()
    parsed_doc = await parser.parse(sample_document.encode("utf-8"), "safety.md", "text/markdown")

    assert parsed_doc.title == "safety.md"
    assert len(parsed_doc.sections) == 2
    assert parsed_doc.sections[0].title == "Machine Safety Manual"

    chunker = DocumentChunker(chunk_size=128, chunk_overlap=16)
    chunks = chunker.create_chunks(
        parsed_doc=parsed_doc,
        tenant_id="00000000-0000-0000-0000-000000000001",
        workspace_id="00000000-0000-0000-0000-000000000002",
        knowledge_base_id="00000000-0000-0000-0000-000000000003",
        document_id="00000000-0000-0000-0000-000000000004",
        document_version_id="00000000-0000-0000-0000-000000000005"
    )

    assert len(chunks) >= 2
    assert chunks[0].section_title == "Machine Safety Manual"
    assert chunks[0].tenant_id == "00000000-0000-0000-0000-000000000001"


@pytest.mark.asyncio
async def test_end_to_end_document_upload_api(async_client: AsyncClient):
    # 1. Register and login tenant admin
    reg = await async_client.post("/api/v1/auth/register", json={
        "tenant_name": "Ingestion Corp",
        "tenant_slug": "ingestion-corp",
        "admin_email": "admin@ingestion-corp.com",
        "admin_password": "IngestionPassword123!"
    })
    assert reg.status_code == 201

    login = await async_client.post("/api/v1/auth/login", json={
        "email": "admin@ingestion-corp.com",
        "password": "IngestionPassword123!",
        "tenant_slug": "ingestion-corp"
    })
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Create Workspace
    ws = await async_client.post("/api/v1/workspaces", json={"name": "WS", "slug": "ws"}, headers=headers)
    ws_id = ws.json()["id"]

    # 3. Create Knowledge Base
    kb = await async_client.post("/api/v1/knowledge-bases", json={
        "workspace_id": ws_id,
        "name": "KB",
        "slug": "kb",
        "embedding_model": "bge-m3"
    }, headers=headers)
    kb_id = kb.json()["id"]

    # 4. Upload File via Multipart Endpoint
    file_content = b"# Operating Procedure\n1. Check power supply.\n2. Start main motor."
    files = {"file": ("procedure.txt", file_content, "text/plain")}
    data = {
        "workspace_id": ws_id,
        "knowledge_base_id": kb_id,
        "title": "Operating Procedure SOP"
    }

    upload_res = await async_client.post("/api/v1/documents/upload", data=data, files=files, headers=headers)
    assert upload_res.status_code == 201
    doc_data = upload_res.json()
    assert doc_data["title"] == "Operating Procedure SOP"
    assert len(doc_data["versions"]) == 1
    assert doc_data["versions"][0]["status"] == "READY"
    assert doc_data["versions"][0]["file_name"] == "procedure.txt"
