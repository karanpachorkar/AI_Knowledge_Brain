import uuid
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.rbac import Permission, Role
from app.schemas.rbac import RoleCreate, RoleUpdate

DEFAULT_PERMISSIONS = [
    ("document.read", "Read documents and chunks"),
    ("document.upload", "Upload new document versions"),
    ("document.delete", "Delete documents and versions"),
    ("document.manage", "Manage document settings and ACLs"),
    ("knowledgebase.read", "View knowledge base details"),
    ("knowledgebase.manage", "Create, edit, or delete knowledge bases"),
    ("chat.use", "Interact with AI RAG chat system"),
    ("user.manage", "Manage user accounts within tenant"),
    ("role.manage", "Manage roles and permissions within tenant"),
    ("audit.read", "View audit trail logs"),
    ("model.manage", "Configure AI models and gateways"),
    ("system.manage", "Manage tenant system settings"),
]


class RBACRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def seed_permissions(self) -> List[Permission]:
        """Seeds standard permissions into database if not present."""
        existing = await self.list_permissions()
        existing_names = {p.name for p in existing}
        
        new_permissions = []
        for name, desc in DEFAULT_PERMISSIONS:
            if name not in existing_names:
                perm = Permission(name=name, description=desc)
                self.session.add(perm)
                new_permissions.append(perm)
        
        if new_permissions:
            await self.session.flush()
        return await self.list_permissions()

    async def list_permissions(self) -> List[Permission]:
        result = await self.session.execute(select(Permission))
        return list(result.scalars().all())

    async def get_permissions_by_ids(self, perm_ids: List[uuid.UUID]) -> List[Permission]:
        result = await self.session.execute(select(Permission).where(Permission.id.in_(perm_ids)))
        return list(result.scalars().all())

    async def create_role(self, tenant_id: uuid.UUID, role_in: RoleCreate) -> Role:
        role = Role(
            tenant_id=tenant_id,
            name=role_in.name,
            description=role_in.description
        )
        if role_in.permission_ids:
            perms = await self.get_permissions_by_ids(role_in.permission_ids)
            role.permissions = perms

        self.session.add(role)
        await self.session.flush()
        return role

    async def get_role_by_id(self, role_id: uuid.UUID, tenant_id: uuid.UUID) -> Optional[Role]:
        result = await self.session.execute(
            select(Role)
            .options(selectinload(Role.permissions))
            .where(Role.id == role_id, Role.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def list_roles_by_tenant(self, tenant_id: uuid.UUID) -> List[Role]:
        result = await self.session.execute(
            select(Role)
            .options(selectinload(Role.permissions))
            .where(Role.tenant_id == tenant_id)
        )
        return list(result.scalars().all())

    async def get_role_by_name(self, tenant_id: uuid.UUID, name: str) -> Optional[Role]:
        result = await self.session.execute(
            select(Role)
            .options(selectinload(Role.permissions))
            .where(Role.tenant_id == tenant_id, Role.name == name)
        )
        return result.scalar_one_or_none()

    async def update_role(self, role: Role, role_in: RoleUpdate) -> Role:
        if role_in.name is not None:
            role.name = role_in.name
        if role_in.description is not None:
            role.description = role_in.description
        if role_in.permission_ids is not None:
            perms = await self.get_permissions_by_ids(role_in.permission_ids)
            role.permissions = perms

        self.session.add(role)
        await self.session.flush()
        return role
