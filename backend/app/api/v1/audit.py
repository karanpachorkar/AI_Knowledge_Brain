import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_tenant_id, require_permission
from app.core.database import get_db
from app.models.user import User
from app.repositories.audit_repository import AuditRepository
from app.schemas.audit import AuditLogResponse

router = APIRouter(prefix="/audit-logs")


@router.get("", response_model=List[AuditLogResponse])
async def list_tenant_audit_logs(
    action: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    _: User = Depends(require_permission("user.manage")),
    db: AsyncSession = Depends(get_db)
):
    """Lists audit logs for active tenant (RBAC: user.manage)."""
    audit_repo = AuditRepository(db)
    return await audit_repo.list_tenant_audit_logs(
        tenant_id=tenant_id,
        action_filter=action,
        skip=skip,
        limit=limit
    )
