import uuid
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.document import Document, DocumentACL, DocumentVersion
from app.schemas.document import DocumentCreate, DocumentVersionCreate


class DocumentRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_document(self, tenant_id: uuid.UUID, user_id: uuid.UUID, doc_in: DocumentCreate) -> Document:
        doc = Document(
            tenant_id=tenant_id,
            workspace_id=doc_in.workspace_id,
            knowledge_base_id=doc_in.knowledge_base_id,
            document_type_id=doc_in.document_type_id,
            title=doc_in.title,
            description=doc_in.description,
            created_by_user_id=user_id
        )
        self.session.add(doc)
        await self.session.flush()
        return doc

    async def get_document_by_id(self, doc_id: uuid.UUID, tenant_id: uuid.UUID) -> Optional[Document]:
        result = await self.session.execute(
            select(Document)
            .options(
                selectinload(Document.document_type),
                selectinload(Document.versions),
                selectinload(Document.acls)
            )
            .where(Document.id == doc_id, Document.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def list_by_knowledge_base(self, kb_id: uuid.UUID, tenant_id: uuid.UUID, skip: int = 0, limit: int = 100) -> List[Document]:
        result = await self.session.execute(
            select(Document)
            .options(
                selectinload(Document.document_type),
                selectinload(Document.versions),
                selectinload(Document.acls)
            )
            .where(Document.knowledge_base_id == kb_id, Document.tenant_id == tenant_id)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_by_tenant(self, tenant_id: uuid.UUID, skip: int = 0, limit: int = 100) -> List[Document]:
        result = await self.session.execute(
            select(Document)
            .options(
                selectinload(Document.document_type),
                selectinload(Document.versions),
                selectinload(Document.acls)
            )
            .where(Document.tenant_id == tenant_id)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def create_version(self, tenant_id: uuid.UUID, doc_id: uuid.UUID, user_id: uuid.UUID, ver_in: DocumentVersionCreate, version_num: int) -> DocumentVersion:
        version = DocumentVersion(
            tenant_id=tenant_id,
            document_id=doc_id,
            version_number=version_num,
            file_name=ver_in.file_name,
            file_size=ver_in.file_size,
            mime_type=ver_in.mime_type,
            checksum=ver_in.checksum,
            storage_key=ver_in.storage_key,
            status="UPLOADED",
            uploaded_by_user_id=user_id,
            metadata_json=ver_in.metadata_json or {}
        )
        self.session.add(version)
        await self.session.flush()
        return version

    async def add_acl(self, tenant_id: uuid.UUID, doc_id: uuid.UUID, role_id: Optional[uuid.UUID] = None, user_id: Optional[uuid.UUID] = None, permission_level: str = "read") -> DocumentACL:
        acl = DocumentACL(
            tenant_id=tenant_id,
            document_id=doc_id,
            role_id=role_id,
            user_id=user_id,
            permission_level=permission_level
        )
        self.session.add(acl)
        await self.session.flush()
        return acl

    async def get_version_by_id(self, version_id: uuid.UUID, tenant_id: uuid.UUID) -> Optional[DocumentVersion]:
        result = await self.session.execute(
            select(DocumentVersion).where(DocumentVersion.id == version_id, DocumentVersion.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def delete_document(self, doc_id: uuid.UUID, tenant_id: uuid.UUID) -> bool:
        doc = await self.get_document_by_id(doc_id, tenant_id)
        if not doc:
            return False
        await self.session.delete(doc)
        await self.session.flush()
        return True

