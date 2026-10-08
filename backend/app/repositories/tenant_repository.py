import uuid
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.tenant import Tenant
from app.schemas.tenant import TenantCreate, TenantUpdate


class TenantRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, tenant_in: TenantCreate) -> Tenant:
        tenant = Tenant(
            name=tenant_in.name,
            slug=tenant_in.slug.lower().strip(),
            config=tenant_in.config or {}
        )
        self.session.add(tenant)
        await self.session.flush()
        return tenant

    async def get_by_id(self, tenant_id: uuid.UUID) -> Optional[Tenant]:
        result = await self.session.execute(select(Tenant).where(Tenant.id == tenant_id))
        return result.scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> Optional[Tenant]:
        result = await self.session.execute(select(Tenant).where(Tenant.slug == slug.lower().strip()))
        return result.scalar_one_or_none()

    async def list_all(self, skip: int = 0, limit: int = 100) -> List[Tenant]:
        result = await self.session.execute(select(Tenant).offset(skip).limit(limit))
        return list(result.scalars().all())

    async def update(self, tenant: Tenant, tenant_in: TenantUpdate) -> Tenant:
        update_data = tenant_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(tenant, field, value)
        self.session.add(tenant)
        await self.session.flush()
        return tenant
