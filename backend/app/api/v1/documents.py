import uuid
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_tenant_id, get_current_user, require_permission
from app.core.database import get_db
from app.models.user import User
from app.repositories.document_repository import DocumentRepository
from app.repositories.knowledge_base_repository import KnowledgeBaseRepository
from app.schemas.document import DocumentCreate, DocumentResponse, DocumentVersionCreate, DocumentVersionResponse
from app.services.ingestion_service import DocumentIngestionService
from app.infrastructure.storage.minio_provider import MinIOStorageProvider
from app.infrastructure.vector.qdrant_provider import QdrantVectorProvider

router = APIRouter(prefix="/documents")


@router.get("/kb/{kb_id}", response_model=List[DocumentResponse])
async def list_documents(
    kb_id: uuid.UUID,
    skip: int = 0,
    limit: int = 100,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    _: User = Depends(require_permission("document.read")),
    db: AsyncSession = Depends(get_db)
):
    """Lists documents within a Knowledge Base or tenant."""
    doc_repo = DocumentRepository(db)
    docs = await doc_repo.list_by_knowledge_base(kb_id, tenant_id, skip=skip, limit=limit)
    if not docs:
        docs = await doc_repo.list_by_tenant(tenant_id, skip=skip, limit=limit)
    return docs


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def create_document(
    doc_in: DocumentCreate,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    current_user: User = Depends(require_permission("document.upload")),
    db: AsyncSession = Depends(get_db)
):
    """Creates a new Document metadata record."""
    kb_repo = KnowledgeBaseRepository(db)
    doc_repo = DocumentRepository(db)

    kb = await kb_repo.get_by_id(doc_in.knowledge_base_id, tenant_id)
    if not kb:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge Base not found.")

    doc = await doc_repo.create_document(tenant_id, current_user.id, doc_in)
    await db.commit()
    return await doc_repo.get_document_by_id(doc.id, tenant_id)


@router.post("/{doc_id}/versions", response_model=DocumentVersionResponse, status_code=status.HTTP_201_CREATED)
async def add_document_version(
    doc_id: uuid.UUID,
    ver_in: DocumentVersionCreate,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    current_user: User = Depends(require_permission("document.upload")),
    db: AsyncSession = Depends(get_db)
):
    """Adds a new version to an existing document."""
    doc_repo = DocumentRepository(db)
    doc = await doc_repo.get_document_by_id(doc_id, tenant_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    version_num = len(doc.versions) + 1
    version = await doc_repo.create_version(tenant_id, doc.id, current_user.id, ver_in, version_num)
    await db.commit()
    return version


@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document_file(
    workspace_id: uuid.UUID = Form(...),
    knowledge_base_id: uuid.UUID = Form(...),
    title: str = Form(...),
    file: UploadFile = File(...),
    document_type_id: Optional[uuid.UUID] = Form(None),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    current_user: User = Depends(require_permission("document.upload")),
    db: AsyncSession = Depends(get_db)
):
    """Uploads document binary, validates checksum, stores in MinIO, and queues async background processing."""
    ingestion_service = DocumentIngestionService(db)
    doc, _ = await ingestion_service.upload_and_process_document(
        tenant_id=tenant_id,
        user_id=current_user.id,
        workspace_id=workspace_id,
        knowledge_base_id=knowledge_base_id,
        title=title,
        file_stream=file.file,
        file_name=file.filename or "uploaded_document",
        mime_type=file.content_type or "application/octet-stream",
        document_type_id=document_type_id,
        run_async=True
    )
    doc_repo = DocumentRepository(db)
    return await doc_repo.get_document_by_id(doc.id, tenant_id)


@router.get("/{doc_id}", response_model=DocumentResponse)
async def get_document(
    doc_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    _: User = Depends(require_permission("document.read")),
    db: AsyncSession = Depends(get_db)
):
    """Retrieves document details and versions."""
    doc_repo = DocumentRepository(db)
    doc = await doc_repo.get_document_by_id(doc_id, tenant_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
    return doc


@router.post("/{doc_id}/retry", response_model=DocumentResponse)
async def retry_document_ingestion(
    doc_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    _: User = Depends(require_permission("document.upload")),
    db: AsyncSession = Depends(get_db)
):
    """Retries async processing for a failed document."""
    ingestion_service = DocumentIngestionService(db)
    await ingestion_service.retry_document_processing(doc_id, tenant_id)
    doc_repo = DocumentRepository(db)
    doc = await doc_repo.get_document_by_id(doc_id, tenant_id)
    return doc


@router.get("/{doc_id}/file")
async def download_document_file(
    doc_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    _: User = Depends(require_permission("document.read")),
    db: AsyncSession = Depends(get_db)
):
    """Streams the raw binary file for a document version — used by the in-app file viewer."""
    doc_repo = DocumentRepository(db)
    doc = await doc_repo.get_document_by_id(doc_id, tenant_id)
    if not doc or not doc.versions:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document or file not found.")

    latest_version = doc.versions[-1]
    bucket_name = f"tenant-{tenant_id}"
    storage = MinIOStorageProvider()

    try:
        file_bytes = await storage.download_file(bucket_name, latest_version.storage_key)
    except FileNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File binary not found in storage.")

    mime = latest_version.mime_type or "application/octet-stream"
    file_name = latest_version.file_name or "document"

    return Response(
        content=file_bytes,
        media_type=mime,
        headers={
            "Content-Disposition": f'inline; filename="{file_name}"',
            "Content-Length": str(len(file_bytes)),
        }
    )


@router.get("/{doc_id}/chunks")
async def get_document_chunks(
    doc_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    _: User = Depends(require_permission("document.read")),
    db: AsyncSession = Depends(get_db)
) -> List[Dict[str, Any]]:
    """Returns all indexed Qdrant vector chunks for a specific document — used by the chunk inspector view."""
    doc_repo = DocumentRepository(db)
    doc = await doc_repo.get_document_by_id(doc_id, tenant_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    qdrant = QdrantVectorProvider()

    # Scroll all points for this document using filter (no vector needed)
    try:
        import httpx
        from app.core.config import settings
        filter_payload = {
            "filter": {
                "must": [
                    {"key": "tenant_id", "match": {"value": str(tenant_id)}},
                    {"key": "document_id", "match": {"value": str(doc_id)}}
                ]
            },
            "limit": 500,
            "with_payload": True,
            "with_vector": False
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.post(
                f"{settings.QDRANT_URL}/collections/{qdrant.collection_name}/points/scroll",
                json=filter_payload
            )
            if res.status_code == 200:
                points = res.json().get("result", {}).get("points", [])
                chunks = [
                    {
                        "chunk_id": pt["id"],
                        "chunk_index": pt["payload"].get("chunk_index", 0),
                        "section_title": pt["payload"].get("section_title"),
                        "page_number": pt["payload"].get("page_number"),
                        "content": pt["payload"].get("content", ""),
                        "metadata": pt["payload"].get("metadata", {}),
                    }
                    for pt in points
                ]
                chunks.sort(key=lambda c: c["chunk_index"])
                return chunks
    except Exception:
        pass

    # Memory store fallback (dev / no Qdrant)
    chunks_from_memory = [
        {
            "chunk_id": pt["id"],
            "chunk_index": pt["payload"].get("chunk_index", 0),
            "section_title": pt["payload"].get("section_title"),
            "page_number": pt["payload"].get("page_number"),
            "content": pt["payload"].get("content", ""),
            "metadata": pt["payload"].get("metadata", {}),
        }
        for pt in qdrant._shared_memory_vectors
        if str(pt["payload"].get("tenant_id")) == str(tenant_id)
        and str(pt["payload"].get("document_id")) == str(doc_id)
    ]
    chunks_from_memory.sort(key=lambda c: c["chunk_index"])
    return chunks_from_memory


@router.delete("/{doc_id}", status_code=status.HTTP_200_OK)
async def delete_document(
    doc_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    _: User = Depends(require_permission("document.delete")),
    db: AsyncSession = Depends(get_db)
):
    """Deletes document across PostgreSQL, MinIO storage, Qdrant vectors, and OpenSearch index."""
    ingestion_service = DocumentIngestionService(db)
    deleted = await ingestion_service.delete_document_complete(doc_id, tenant_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found or already deleted.")
    return {"message": "Document and all derived artifacts deleted successfully", "document_id": str(doc_id)}



