import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_tenant_id, require_permission
from app.core.database import get_db
from app.models.user import User
from app.repositories.knowledge_base_repository import KnowledgeBaseRepository
from app.repositories.workspace_repository import WorkspaceRepository
from app.schemas.knowledge_base import KnowledgeBaseCreate, KnowledgeBaseResponse, KnowledgeBaseUpdate

router = APIRouter(prefix="/knowledge-bases")


@router.get("/workspace/{workspace_id}", response_model=List[KnowledgeBaseResponse])
async def list_knowledge_bases(
    workspace_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    _: User = Depends(require_permission("knowledgebase.read")),
    db: AsyncSession = Depends(get_db)
):
    """Lists knowledge bases belonging to a specific workspace."""
    kb_repo = KnowledgeBaseRepository(db)
    return await kb_repo.list_by_workspace(workspace_id, tenant_id)


@router.post("", response_model=KnowledgeBaseResponse, status_code=status.HTTP_201_CREATED)
async def create_knowledge_base(
    kb_in: KnowledgeBaseCreate,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    _: User = Depends(require_permission("knowledgebase.manage")),
    db: AsyncSession = Depends(get_db)
):
    """Creates a new Knowledge Base within a workspace."""
    ws_repo = WorkspaceRepository(db)
    kb_repo = KnowledgeBaseRepository(db)

    ws = await ws_repo.get_by_id(kb_in.workspace_id, tenant_id)
    if not ws:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found.")

    existing = await kb_repo.get_by_slug(kb_in.slug, kb_in.workspace_id, tenant_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Knowledge base with slug '{kb_in.slug}' already exists in this workspace."
        )

    kb = await kb_repo.create(tenant_id, kb_in)
    await db.commit()
    return kb


@router.get("/{kb_id}", response_model=KnowledgeBaseResponse)
async def get_knowledge_base(
    kb_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    _: User = Depends(require_permission("knowledgebase.read")),
    db: AsyncSession = Depends(get_db)
):
    """Gets details of a specific Knowledge Base."""
    kb_repo = KnowledgeBaseRepository(db)
    kb = await kb_repo.get_by_id(kb_id, tenant_id)
    if not kb:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge Base not found.")
    return kb
