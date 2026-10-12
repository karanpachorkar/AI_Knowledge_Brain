import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_tenant_id, get_current_user, require_permission
from app.core.database import get_db
from app.models.user import User
from app.repositories.document_repository import DocumentRepository
from app.repositories.knowledge_base_repository import KnowledgeBaseRepository
from app.schemas.document import DocumentCreate, DocumentResponse, DocumentVersionCreate, DocumentVersionResponse
from app.services.ingestion_service import DocumentIngestionService

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



