import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_tenant_id, require_permission
from app.core.database import get_db
from app.models.user import User
from app.repositories.rbac_repository import RBACRepository
from app.schemas.rbac import PermissionResponse, RoleCreate, RoleResponse, RoleUpdate

router = APIRouter(prefix="/roles")


@router.get("/permissions", response_model=List[PermissionResponse])
async def list_permissions(
    _: User = Depends(require_permission("role.manage")),
    db: AsyncSession = Depends(get_db)
):
    """Lists all system permissions available for role assignment."""
    rbac_repo = RBACRepository(db)
    return await rbac_repo.list_permissions()


@router.get("", response_model=List[RoleResponse])
async def list_roles(
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    _: User = Depends(require_permission("role.manage")),
    db: AsyncSession = Depends(get_db)
):
    """Lists custom roles configured within current tenant."""
    rbac_repo = RBACRepository(db)
    return await rbac_repo.list_roles_by_tenant(tenant_id)


@router.post("", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
async def create_role(
    role_in: RoleCreate,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    _: User = Depends(require_permission("role.manage")),
    db: AsyncSession = Depends(get_db)
):
    """Creates a new role within active tenant (RBAC: role.manage)."""
    rbac_repo = RBACRepository(db)
    existing = await rbac_repo.get_role_by_name(tenant_id, role_in.name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Role with name '{role_in.name}' already exists."
        )

    role = await rbac_repo.create_role(tenant_id, role_in)
    await db.commit()
    return await rbac_repo.get_role_by_id(role.id, tenant_id)
