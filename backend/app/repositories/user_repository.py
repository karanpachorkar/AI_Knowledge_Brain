import uuid
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.models.rbac import Role
from app.schemas.user import UserCreate, UserUpdate


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, tenant_id: uuid.UUID, user_in: UserCreate, hashed_password: str, roles: Optional[List[Role]] = None) -> User:
        user = User(
            tenant_id=tenant_id,
            email=user_in.email.lower().strip(),
            hashed_password=hashed_password,
            full_name=user_in.full_name,
            is_active=True,
            is_superuser=False
        )
        if roles:
            user.roles = roles
        self.session.add(user)
        await self.session.flush()
        return user

    async def get_by_id(self, user_id: uuid.UUID, tenant_id: Optional[uuid.UUID] = None) -> Optional[User]:
        query = (
            select(User)
            .options(
                selectinload(User.tenant),
                selectinload(User.roles).selectinload(Role.permissions)
            )
            .where(User.id == user_id)
        )
        if tenant_id:
            query = query.where(User.tenant_id == tenant_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str, tenant_id: Optional[uuid.UUID] = None) -> Optional[User]:
        query = (
            select(User)
            .options(
                selectinload(User.tenant),
                selectinload(User.roles).selectinload(Role.permissions)
            )
            .where(User.email == email.lower().strip())
        )
        if tenant_id:
            query = query.where(User.tenant_id == tenant_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def list_by_tenant(self, tenant_id: uuid.UUID, skip: int = 0, limit: int = 100) -> List[User]:
        query = (
            select(User)
            .options(
                selectinload(User.roles).selectinload(Role.permissions)
            )
            .where(User.tenant_id == tenant_id)
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def list_all(self, skip: int = 0, limit: int = 100) -> List[User]:
        query = (
            select(User)
            .options(
                selectinload(User.tenant),
                selectinload(User.roles).selectinload(Role.permissions)
            )
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update(self, user: User, user_in: UserUpdate, hashed_password: Optional[str] = None, roles: Optional[List[Role]] = None) -> User:
        if user_in.full_name is not None:
            user.full_name = user_in.full_name
        if user_in.is_active is not None:
            user.is_active = user_in.is_active
        if hashed_password is not None:
            user.hashed_password = hashed_password
        if roles is not None:
            user.roles = roles

        self.session.add(user)
        await self.session.flush()
        return user
