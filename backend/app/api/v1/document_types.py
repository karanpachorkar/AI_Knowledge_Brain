import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_tenant_id, require_permission
from app.core.database import get_db
from app.models.user import User
from app.repositories.document_type_repository import DocumentTypeRepository
from app.schemas.document_type import DocumentTypeCreate, DocumentTypeResponse, DocumentTypeUpdate

router = APIRouter(prefix="/document-types")


@router.get("", response_model=List[DocumentTypeResponse])
async def list_document_types(
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    _: User = Depends(require_permission("document.read")),
    db: AsyncSession = Depends(get_db)
):
    """Lists configurable document types for current tenant (auto-seeds defaults if empty)."""
    dt_repo = DocumentTypeRepository(db)
    types = await dt_repo.list_by_tenant(tenant_id)
    if not types:
        types = await dt_repo.seed_defaults_for_tenant(tenant_id)
        await db.commit()
    return types


@router.post("", response_model=DocumentTypeResponse, status_code=status.HTTP_201_CREATED)
async def create_document_type(
    dt_in: DocumentTypeCreate,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    _: User = Depends(require_permission("document.manage")),
    db: AsyncSession = Depends(get_db)
):
    """Creates a custom document type configuration."""
    dt_repo = DocumentTypeRepository(db)
    dt = await dt_repo.create(tenant_id, dt_in)
    await db.commit()
    return dt
