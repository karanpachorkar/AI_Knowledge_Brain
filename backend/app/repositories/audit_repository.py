import uuid
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.audit import AuditLog


class AuditRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def log_event(
        self,
        tenant_id: uuid.UUID | str,
        user_id: Optional[uuid.UUID | str],
        action: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        metadata_json: Optional[dict] = None
    ) -> AuditLog:
        t_id = uuid.UUID(str(tenant_id)) if isinstance(tenant_id, str) else tenant_id
        u_id = uuid.UUID(str(user_id)) if user_id and isinstance(user_id, str) else user_id

        log_entry = AuditLog(
            tenant_id=t_id,
            user_id=u_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata_json=metadata_json
        )
        self.session.add(log_entry)
        await self.session.flush()
        return log_entry

    async def list_tenant_audit_logs(
        self,
        tenant_id: uuid.UUID,
        action_filter: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[AuditLog]:
        stmt = select(AuditLog).where(AuditLog.tenant_id == tenant_id)
        if action_filter:
            stmt = stmt.where(AuditLog.action == action_filter)
        stmt = stmt.order_by(AuditLog.created_at.desc()).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
