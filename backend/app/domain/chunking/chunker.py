import uuid
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from app.infrastructure.parsers.base import ParsedDocument


class DocumentChunk(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    workspace_id: str
    knowledge_base_id: str
    document_id: str
    document_version_id: str
    chunk_index: int
    content: str
    section_title: Optional[str] = None
    page_number: Optional[int] = None
    metadata: Dict = Field(default_factory=dict)


class DocumentChunker:
    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 64):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def create_chunks(
        self,
        parsed_doc: ParsedDocument,
        tenant_id: uuid.UUID,
        workspace_id: uuid.UUID,
        knowledge_base_id: uuid.UUID,
        document_id: uuid.UUID,
        document_version_id: uuid.UUID
    ) -> List[DocumentChunk]:
        chunks: List[DocumentChunk] = []
        chunk_index = 0

        for section in parsed_doc.sections:
            text = section.content.strip()
            if not text:
                continue

            # Heading-aware chunk splitting
            start = 0
            text_length = len(text)

            while start < text_length:
                end = start + self.chunk_size
                chunk_text = text[start:end]

                # Adjust boundary to end of word if possible
                if end < text_length:
                    last_space = chunk_text.rfind(" ")
                    if last_space > self.chunk_size // 2:
                        end = start + last_space
                        chunk_text = text[start:end]

                formatted_chunk = f"Section: {section.title or 'Overview'}\n{chunk_text.strip()}"

                chunks.append(
                    DocumentChunk(
                        tenant_id=str(tenant_id),
                        workspace_id=str(workspace_id),
                        knowledge_base_id=str(knowledge_base_id),
                        document_id=str(document_id),
                        document_version_id=str(document_version_id),
                        chunk_index=chunk_index,
                        content=formatted_chunk,
                        section_title=section.title,
                        page_number=section.page_number,
                        metadata={
                            "document_title": parsed_doc.title,
                            "chunk_size": len(formatted_chunk),
                            "is_table": section.is_table
                        }
                    )
                )
                chunk_index += 1
                start += max(1, self.chunk_size - self.chunk_overlap)

        return chunks
