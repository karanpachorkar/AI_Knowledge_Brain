import uuid
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.document_type import DocumentType
from app.schemas.document_type import DocumentTypeCreate, DocumentTypeUpdate

DEFAULT_DOCUMENT_TYPES = [
    ("Standard Operating Procedure", "SOP", "Standard Operating Procedure documentation"),
    ("User Requirements Specification", "URS", "User Requirements Specification document"),
    ("Corrective Action Preventive Action", "CAPA", "CAPA investigation and resolution report"),
    ("Machine Operating Manual", "MANUAL", "Technical operating and maintenance manual"),
    ("Validation Specification", "VAL_SPEC", "System validation specification document"),
]


class DocumentTypeRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def seed_defaults_for_tenant(self, tenant_id: uuid.UUID) -> List[DocumentType]:
        existing = await self.list_by_tenant(tenant_id)
        existing_codes = {dt.code for dt in existing}

        new_types = []
        for name, code, desc in DEFAULT_DOCUMENT_TYPES:
            if code not in existing_codes:
                dt = DocumentType(
                    tenant_id=tenant_id,
                    name=name,
                    code=code,
                    description=desc,
                    schema_definition={},
                    is_active=True
                )
                self.session.add(dt)
                new_types.append(dt)

        if new_types:
            await self.session.flush()
        return await self.list_by_tenant(tenant_id)

    async def create(self, tenant_id: uuid.UUID, dt_in: DocumentTypeCreate) -> DocumentType:
        dt = DocumentType(
            tenant_id=tenant_id,
            name=dt_in.name,
            code=dt_in.code.upper().strip(),
            description=dt_in.description,
            schema_definition=dt_in.schema_definition or {},
            is_active=True
        )
        self.session.add(dt)
        await self.session.flush()
        return dt

    async def get_by_id(self, dt_id: uuid.UUID, tenant_id: uuid.UUID) -> Optional[DocumentType]:
        result = await self.session.execute(
            select(DocumentType).where(DocumentType.id == dt_id, DocumentType.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def list_by_tenant(self, tenant_id: uuid.UUID) -> List[DocumentType]:
        result = await self.session.execute(
            select(DocumentType).where(DocumentType.tenant_id == tenant_id)
        )
        return list(result.scalars().all())

    async def update(self, dt: DocumentType, dt_in: DocumentTypeUpdate) -> DocumentType:
        update_data = dt_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(dt, field, value)
        self.session.add(dt)
        await self.session.flush()
        return dt
