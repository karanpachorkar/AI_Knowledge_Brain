import uuid
import asyncio
from datetime import datetime, timezone
from typing import BinaryIO, Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.domain.chunking.chunker import DocumentChunker
from app.infrastructure.parsers.standard_parser import StandardDocumentParser
from app.infrastructure.storage.minio_provider import MinIOStorageProvider
from app.infrastructure.vector.qdrant_provider import QdrantVectorProvider
from app.infrastructure.search.opensearch_provider import OpenSearchProvider
from app.models.document import Document, DocumentVersion
from app.repositories.document_repository import DocumentRepository
from app.repositories.knowledge_base_repository import KnowledgeBaseRepository
from app.schemas.document import DocumentCreate, DocumentVersionCreate
from app.services.file_validation_service import FileValidationService
from app.services.indexing_service import IndexingService


class DocumentIngestionService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.doc_repo = DocumentRepository(session)
        self.kb_repo = KnowledgeBaseRepository(session)
        self.storage = MinIOStorageProvider()
        self.parser = StandardDocumentParser()
        self.indexing_service = IndexingService()
        self.qdrant = QdrantVectorProvider()
        self.opensearch = OpenSearchProvider()

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
        document_type_id: Optional[uuid.UUID] = None,
        run_async: bool = True
    ) -> Tuple[Document, DocumentVersion]:
        """Uploads document binary to MinIO, creates DB records with QUEUED status, and queues processing job."""
        # 1. Validate Knowledge Base exists or auto-provision for tenant
        kb = await self.kb_repo.get_by_id(knowledge_base_id, tenant_id)
        if not kb:
            from app.repositories.workspace_repository import WorkspaceRepository
            from app.schemas.workspace import WorkspaceCreate
            from app.schemas.knowledge_base import KnowledgeBaseCreate

            ws_repo = WorkspaceRepository(self.session)
            ws = await ws_repo.get_by_id(workspace_id, tenant_id)
            if not ws:
                workspaces = await ws_repo.list_by_tenant(tenant_id)
                if workspaces:
                    ws = workspaces[0]
                else:
                    ws = await ws_repo.create(
                        tenant_id=tenant_id,
                        ws_in=WorkspaceCreate(
                            name="Default Workspace",
                            slug="default-workspace",
                            description="Default Workspace"
                        )
                    )
                workspace_id = ws.id

            kbs = await self.kb_repo.list_by_workspace(workspace_id, tenant_id)
            if kbs:
                kb = kbs[0]
            else:
                kb = await self.kb_repo.create(
                    tenant_id=tenant_id,
                    kb_in=KnowledgeBaseCreate(
                        workspace_id=workspace_id,
                        name="Default Knowledge Base",
                        slug="default-kb",
                        description="Default Knowledge Base"
                    )
                )
            knowledge_base_id = kb.id

        # 2. File Validation & Checksum Calculation
        checksum, file_size = FileValidationService.calculate_checksum_and_validate(
            file_stream=file_stream,
            file_name=file_name,
            mime_type=mime_type
        )

        # 3. MinIO Object Storage Upload (Original file safely stored)
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

        # 5. Create Document Version Record with status "QUEUED"
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
        version.status = "QUEUED"
        self.session.add(version)
        await self.session.commit()

        # 6. Queue processing job in background or process async task
        is_sqlite = False
        try:
            bind_url = str(getattr(self.session.bind, "url", ""))
            if "sqlite" in bind_url:
                is_sqlite = True
        except Exception:
            pass


        if run_async and not is_sqlite:
            asyncio.create_task(self.process_document_version(version.id, tenant_id))
        else:
            await self.process_document_version(version.id, tenant_id, db=self.session)

        return doc, version


    async def process_document_version(
        self,
        version_id: uuid.UUID,
        tenant_id: uuid.UUID,
        max_retries: int = 3,
        db: Optional[AsyncSession] = None
    ) -> bool:
        """Background worker execution method that processes a document version through granular stages."""
        if db is not None:
            return await self._execute_processing_with_db(db, version_id, tenant_id, max_retries)

        from app.core.database import AsyncSessionLocal
        async with AsyncSessionLocal() as session:
            return await self._execute_processing_with_db(session, version_id, tenant_id, max_retries)

    async def _execute_processing_with_db(
        self,
        db: AsyncSession,
        version_id: uuid.UUID,
        tenant_id: uuid.UUID,
        max_retries: int = 3
    ) -> bool:
        doc_repo = DocumentRepository(db)
        kb_repo = KnowledgeBaseRepository(db)
        
        version = await doc_repo.get_version_by_id(version_id, tenant_id)
        if not version:
            logger.error("Document version not found for processing", version_id=str(version_id))
            return False

        if version.status == "READY":
            logger.info("Document version is already READY, skipping idempotent processing", version_id=str(version_id))
            return True

        doc = await doc_repo.get_document_by_id(version.document_id, tenant_id)
        if not doc:
            logger.error("Parent document not found for version", version_id=str(version_id))
            return False

        kb = await kb_repo.get_by_id(doc.knowledge_base_id, tenant_id)
        if not kb:
            logger.error("Knowledge base not found for document", version_id=str(version_id))
            return False

        bucket_name = f"tenant-{tenant_id}"
        meta = version.metadata_json or {}
        retry_count = meta.get("retry_count", 0)

        try:
            # Stage: PROCESSING
            version.status = "PROCESSING"
            db.add(version)
            await db.commit()

            # Download binary from MinIO
            file_bytes = await self.storage.download_file(bucket_name, version.storage_key)

            # Stage: OCR / Parsing
            version.status = "OCR"
            db.add(version)
            await db.commit()
            parsed_doc = await self.parser.parse(file_bytes, version.file_name, version.mime_type)

            # Stage: CHUNKING
            version.status = "CHUNKING"
            db.add(version)
            await db.commit()
            chunker = DocumentChunker(chunk_size=kb.chunk_size, chunk_overlap=kb.chunk_overlap)
            chunks = chunker.create_chunks(
                parsed_doc=parsed_doc,
                tenant_id=tenant_id,
                workspace_id=doc.workspace_id,
                knowledge_base_id=doc.knowledge_base_id,
                document_id=doc.id,
                document_version_id=version.id
            )

            # Stage: EMBEDDING & INDEXING
            version.status = "EMBEDDING"
            db.add(version)
            await db.commit()

            version.status = "INDEXING"
            db.add(version)
            await db.commit()
            await self.indexing_service.index_chunks(chunks)

            # Stage: READY
            version.status = "READY"
            meta["parsed_sections"] = len(parsed_doc.sections)
            meta["generated_chunks"] = len(chunks)
            meta["completed_at"] = datetime.now(timezone.utc).isoformat()
            version.metadata_json = meta
            db.add(version)
            await db.commit()

            logger.info("Async document processing completed successfully", document_id=str(doc.id), version_id=str(version.id), chunks=len(chunks))
            return True

        except Exception as e:
            logger.error("Error during document processing", version_id=str(version_id), error=str(e), retry_count=retry_count)
            retry_count += 1
            meta["retry_count"] = retry_count
            meta["error_message"] = str(e)
            meta["last_error_at"] = datetime.now(timezone.utc).isoformat()

            if retry_count < max_retries:
                meta["status_note"] = f"Will retry (attempt {retry_count}/{max_retries})"
                version.metadata_json = meta
                version.status = "QUEUED"
                db.add(version)
                await db.commit()
                # Re-queue retry
                asyncio.create_task(self.process_document_version(version_id, tenant_id, max_retries=max_retries))
            else:
                meta["status_note"] = "Max retries exceeded"
                version.metadata_json = meta
                version.status = "FAILED"
                db.add(version)
                await db.commit()

            return False


    async def retry_document_processing(self, doc_id: uuid.UUID, tenant_id: uuid.UUID) -> bool:
        """Resets failed document version status to QUEUED and re-enqueues processing job."""
        doc = await self.doc_repo.get_document_by_id(doc_id, tenant_id)
        if not doc or not doc.versions:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document or document version not found.")

        version = doc.versions[-1]
        meta = version.metadata_json or {}
        meta["retry_count"] = 0
        meta.pop("error_message", None)
        version.metadata_json = meta
        version.status = "QUEUED"
        self.session.add(version)
        await self.session.commit()

        asyncio.create_task(self.process_document_version(version.id, tenant_id))
        return True

    async def delete_document_complete(self, doc_id: uuid.UUID, tenant_id: uuid.UUID) -> bool:
        """Performs complete document deletion across DB, MinIO storage, Qdrant vectors, and OpenSearch index."""
        doc = await self.doc_repo.get_document_by_id(doc_id, tenant_id)
        if not doc:
            return False

        bucket_name = f"tenant-{tenant_id}"

        # 1. MinIO Storage cleanup for all versions
        for ver in doc.versions:
            if ver.storage_key:
                try:
                    await self.storage.delete_file(bucket_name, ver.storage_key)
                except Exception as e:
                    logger.warning("Failed deleting storage object", key=ver.storage_key, error=str(e))

        # 2. Qdrant vector points cleanup
        await self.qdrant.delete_document_vectors(str(tenant_id), str(doc_id))

        # 3. OpenSearch BM25 chunks cleanup
        await self.opensearch.delete_document_index(str(tenant_id), str(doc_id))

        # 4. PostgreSQL metadata, ACL records, and version cascade deletion
        deleted_db = await self.doc_repo.delete_document(doc_id, tenant_id)
        await self.session.commit()

        logger.info("Complete document deletion finished", document_id=str(doc_id), tenant_id=str(tenant_id))
        return deleted_db

