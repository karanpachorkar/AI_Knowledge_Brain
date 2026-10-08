import uuid
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.knowledge_base import KnowledgeBase
from app.schemas.knowledge_base import KnowledgeBaseCreate, KnowledgeBaseUpdate


class KnowledgeBaseRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, tenant_id: uuid.UUID, kb_in: KnowledgeBaseCreate) -> KnowledgeBase:
        kb = KnowledgeBase(
            tenant_id=tenant_id,
            workspace_id=kb_in.workspace_id,
            name=kb_in.name,
            slug=kb_in.slug.lower().strip(),
            description=kb_in.description,
            embedding_model=kb_in.embedding_model,
            chunk_size=kb_in.chunk_size,
            chunk_overlap=kb_in.chunk_overlap
        )
        self.session.add(kb)
        await self.session.flush()
        return kb

    async def get_by_id(self, kb_id: uuid.UUID, tenant_id: uuid.UUID) -> Optional[KnowledgeBase]:
        result = await self.session.execute(
            select(KnowledgeBase).where(KnowledgeBase.id == kb_id, KnowledgeBase.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def get_by_slug(self, slug: str, workspace_id: uuid.UUID, tenant_id: uuid.UUID) -> Optional[KnowledgeBase]:
        result = await self.session.execute(
            select(KnowledgeBase).where(
                KnowledgeBase.slug == slug.lower().strip(),
                KnowledgeBase.workspace_id == workspace_id,
                KnowledgeBase.tenant_id == tenant_id
            )
        )
        return result.scalar_one_or_none()

    async def list_by_workspace(self, workspace_id: uuid.UUID, tenant_id: uuid.UUID) -> List[KnowledgeBase]:
        result = await self.session.execute(
            select(KnowledgeBase).where(
                KnowledgeBase.workspace_id == workspace_id,
                KnowledgeBase.tenant_id == tenant_id
            )
        )
        return list(result.scalars().all())

    async def update(self, kb: KnowledgeBase, kb_in: KnowledgeBaseUpdate) -> KnowledgeBase:
        update_data = kb_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(kb, field, value)
        self.session.add(kb)
        await self.session.flush()
        return kb
