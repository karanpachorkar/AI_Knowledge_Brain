import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_tenant_id, get_current_user, require_permission
from app.core.database import get_db
from app.core.security import hash_password
from app.models.user import User
from app.repositories.rbac_repository import RBACRepository
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserCreate, UserResponse, UserUpdate
from app.services.auth_service import AuthService

router = APIRouter(prefix="/users")


@router.get("", response_model=List[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    _: User = Depends(require_permission("user.manage")),
    db: AsyncSession = Depends(get_db)
):
    """Lists users belonging to current tenant (RBAC: user.manage)."""
    user_repo = UserRepository(db)
    users = await user_repo.list_by_tenant(tenant_id, skip=skip, limit=limit)
    return [AuthService.format_user_response(u) for u in users]


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_in: UserCreate,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    _: User = Depends(require_permission("user.manage")),
    db: AsyncSession = Depends(get_db)
):
    """Creates a new user within active tenant (RBAC: user.manage)."""
    user_repo = UserRepository(db)
    rbac_repo = RBACRepository(db)

    existing = await user_repo.get_by_email(user_in.email, tenant_id=tenant_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User with email '{user_in.email}' already exists in this tenant."
        )

    roles = []
    if user_in.role_ids:
        for r_id in user_in.role_ids:
            role = await rbac_repo.get_role_by_id(r_id, tenant_id=tenant_id)
            if role:
                roles.append(role)

    hashed_pw = hash_password(user_in.password)
    user = await user_repo.create(
        tenant_id=tenant_id,
        user_in=user_in,
        hashed_password=hashed_pw,
        roles=roles
    )
    await db.commit()
    user = await user_repo.get_by_id(user.id)
    return AuthService.format_user_response(user)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    _: User = Depends(require_permission("user.manage")),
    db: AsyncSession = Depends(get_db)
):
    """Gets details of a specific user within current tenant."""
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_id, tenant_id=tenant_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )
    return AuthService.format_user_response(user)
