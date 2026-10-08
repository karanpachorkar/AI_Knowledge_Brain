import uuid
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.workspace import Workspace
from app.schemas.workspace import WorkspaceCreate, WorkspaceUpdate


class WorkspaceRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, tenant_id: uuid.UUID, ws_in: WorkspaceCreate) -> Workspace:
        workspace = Workspace(
            tenant_id=tenant_id,
            name=ws_in.name,
            slug=ws_in.slug.lower().strip(),
            description=ws_in.description,
            is_active=True
        )
        self.session.add(workspace)
        await self.session.flush()
        return workspace

    async def get_by_id(self, ws_id: uuid.UUID, tenant_id: uuid.UUID) -> Optional[Workspace]:
        result = await self.session.execute(
            select(Workspace).where(Workspace.id == ws_id, Workspace.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def get_by_slug(self, slug: str, tenant_id: uuid.UUID) -> Optional[Workspace]:
        result = await self.session.execute(
            select(Workspace).where(Workspace.slug == slug.lower().strip(), Workspace.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def list_by_tenant(self, tenant_id: uuid.UUID, skip: int = 0, limit: int = 100) -> List[Workspace]:
        result = await self.session.execute(
            select(Workspace).where(Workspace.tenant_id == tenant_id).offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    async def update(self, workspace: Workspace, ws_in: WorkspaceUpdate) -> Workspace:
        update_data = ws_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(workspace, field, value)
        self.session.add(workspace)
        await self.session.flush()
        return workspace
