import uuid
from typing import Callable, List, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_token
from app.models.user import User
from app.repositories.user_repository import UserRepository

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """FastAPI Dependency: Decodes JWT bearer token and retrieves active user."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated. Please log in.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not token:
        raise credentials_exception

    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        raise credentials_exception

    user_id_str: Optional[str] = payload.get("sub")
    if not user_id_str:
        raise credentials_exception

    user_repo = UserRepository(db)
    try:
        user = await user_repo.get_by_id(uuid.UUID(user_id_str))
    except Exception:
        raise credentials_exception

    if not user or not user.is_active:
        raise credentials_exception

    return user



async def get_current_tenant_id(
    current_user: User = Depends(get_current_user)
) -> uuid.UUID:
    """FastAPI Dependency: Enforces tenant context isolation for current request."""
    return current_user.tenant_id


def require_permission(permission_name: str) -> Callable:
    """FastAPI Dependency Factory: Enforces RBAC permission check on endpoint."""
    async def permission_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.is_superuser:
            return current_user

        user_permissions = {p.name for r in current_user.roles for p in r.permissions}
        if permission_name not in user_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation forbidden. Required permission: '{permission_name}'."
            )
        return current_user

    return permission_checker
