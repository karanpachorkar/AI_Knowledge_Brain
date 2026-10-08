import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_tenant_id, require_permission
from app.core.database import get_db
from app.models.user import User
from app.repositories.workspace_repository import WorkspaceRepository
from app.schemas.workspace import WorkspaceCreate, WorkspaceResponse, WorkspaceUpdate

router = APIRouter(prefix="/workspaces")


@router.get("", response_model=List[WorkspaceResponse])
async def list_workspaces(
    skip: int = 0,
    limit: int = 100,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    _: User = Depends(require_permission("knowledgebase.read")),
    db: AsyncSession = Depends(get_db)
):
    """Lists workspaces belonging to the active tenant."""
    ws_repo = WorkspaceRepository(db)
    return await ws_repo.list_by_tenant(tenant_id, skip=skip, limit=limit)


@router.post("", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    ws_in: WorkspaceCreate,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    _: User = Depends(require_permission("knowledgebase.manage")),
    db: AsyncSession = Depends(get_db)
):
    """Creates a new workspace within active tenant."""
    ws_repo = WorkspaceRepository(db)
    existing = await ws_repo.get_by_slug(ws_in.slug, tenant_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Workspace with slug '{ws_in.slug}' already exists."
        )

    workspace = await ws_repo.create(tenant_id, ws_in)
    await db.commit()
    return workspace


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace(
    workspace_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    _: User = Depends(require_permission("knowledgebase.read")),
    db: AsyncSession = Depends(get_db)
):
    """Gets details of a specific workspace."""
    ws_repo = WorkspaceRepository(db)
    ws = await ws_repo.get_by_id(workspace_id, tenant_id)
    if not ws:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found.")
    return ws
