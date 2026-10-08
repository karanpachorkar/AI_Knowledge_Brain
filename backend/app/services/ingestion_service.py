import uuid
from typing import BinaryIO, Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.domain.chunking.chunker import DocumentChunker
from app.infrastructure.parsers.standard_parser import StandardDocumentParser
from app.infrastructure.storage.minio_provider import MinIOStorageProvider
from app.models.document import Document, DocumentVersion
from app.repositories.document_repository import DocumentRepository
from app.repositories.knowledge_base_repository import KnowledgeBaseRepository
from app.schemas.document import DocumentCreate, DocumentVersionCreate
from app.services.file_validation_service import FileValidationService


class DocumentIngestionService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.doc_repo = DocumentRepository(session)
        self.kb_repo = KnowledgeBaseRepository(session)
        self.storage = MinIOStorageProvider()
        self.parser = StandardDocumentParser()

    async def upload_and_process_document(
        self,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        knowledge_base_id: uuid.UUID,
        title: str,
        file_stream: BinaryIO,
        file_name: str,
        mime_type: str,
        document_type_id: Optional[uuid.UUID] = None
    ) -> Tuple[Document, DocumentVersion]:
        # 1. Validate Knowledge Base exists
        kb = await self.kb_repo.get_by_id(knowledge_base_id, tenant_id)
        if not kb:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Target Knowledge Base not found."
            )

        # 2. File Validation & Checksum Calculation
        checksum, file_size = FileValidationService.calculate_checksum_and_validate(
            file_stream=file_stream,
            file_name=file_name,
            mime_type=mime_type
        )

        # 3. MinIO Object Storage Upload
        bucket_name = f"tenant-{tenant_id}"
        storage_key = f"{workspace_id}/{knowledge_base_id}/{uuid.uuid4()}_{file_name}"
        
        await self.storage.upload_file(
            bucket_name=bucket_name,
            object_key=storage_key,
            file_data=file_stream,
            content_length=file_size,
            content_type=mime_type
        )

        # 4. Create Document Record
        doc = await self.doc_repo.create_document(
            tenant_id=tenant_id,
            user_id=user_id,
            doc_in=DocumentCreate(
                workspace_id=workspace_id,
                knowledge_base_id=knowledge_base_id,
                document_type_id=document_type_id,
                title=title
            )
        )

        # 5. Create Document Version Record
        version = await self.doc_repo.create_version(
            tenant_id=tenant_id,
            doc_id=doc.id,
            user_id=user_id,
            ver_in=DocumentVersionCreate(
                file_name=file_name,
                file_size=file_size,
                mime_type=mime_type,
                checksum=checksum,
                storage_key=storage_key
            ),
            version_num=1
        )
        await self.session.commit()

        # 6. Process File Content (Parse & Chunk)
        file_bytes = await self.storage.download_file(bucket_name, storage_key)
        parsed_doc = await self.parser.parse(file_bytes, file_name, mime_type)

        chunker = DocumentChunker(chunk_size=kb.chunk_size, chunk_overlap=kb.chunk_overlap)
        chunks = chunker.create_chunks(
            parsed_doc=parsed_doc,
            tenant_id=tenant_id,
            workspace_id=workspace_id,
            knowledge_base_id=knowledge_base_id,
            document_id=doc.id,
            document_version_id=version.id
        )

        # Update version status to READY
        version.status = "READY"
        version.metadata_json = {
            "parsed_sections": len(parsed_doc.sections),
            "generated_chunks": len(chunks)
        }
        self.session.add(version)
        await self.session.commit()

        logger.info(
            "Document ingestion completed successfully",
            document_id=str(doc.id),
            version_id=str(version.id),
            chunks=len(chunks)
        )
        return doc, version
