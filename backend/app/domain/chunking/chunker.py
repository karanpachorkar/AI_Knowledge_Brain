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


from typing import List, Optional, Union

class DocumentChunker:
    def __init__(self, chunk_size: int = 1500, chunk_overlap: int = 200):
        # Ensure minimum chunk capacity of 1500 chars to avoid fracturing tables and multi-item lists
        self.chunk_size = max(chunk_size, 1500) if chunk_size <= 512 else chunk_size
        self.chunk_overlap = chunk_overlap

    def create_chunks(
        self,
        parsed_doc: ParsedDocument,
        tenant_id: Union[uuid.UUID, str],
        workspace_id: Union[uuid.UUID, str],
        knowledge_base_id: Union[uuid.UUID, str],
        document_id: Union[uuid.UUID, str],
        document_version_id: Union[uuid.UUID, str]
    ) -> List[DocumentChunk]:
        chunks: List[DocumentChunk] = []
        chunk_index = 0

        for section in parsed_doc.sections:
            text = section.content.strip()
            if not text:
                continue

            # If section fits within chunk_size, preserve it completely as 1 chunk (preserves entire tables)
            doc_header = f"Document: {parsed_doc.title} | Section: {section.title or 'Overview'}"
            if len(text) <= self.chunk_size:
                formatted_chunk = f"{doc_header}\n{text}"
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
                continue

            # Otherwise, split along clean paragraph or newline boundaries
            start = 0
            text_length = len(text)

            while start < text_length:
                end = min(start + self.chunk_size, text_length)
                chunk_text = text[start:end]

                if end < text_length:
                    # Look for paragraph break \n\n first
                    para_break = chunk_text.rfind("\n\n")
                    if para_break > self.chunk_size // 2:
                        end = start + para_break + 2
                    else:
                        # Look for newline break \n
                        line_break = chunk_text.rfind("\n")
                        if line_break > self.chunk_size // 2:
                            end = start + line_break + 1
                        else:
                            # Fallback to word space
                            space_break = chunk_text.rfind(" ")
                            if space_break > self.chunk_size // 2:
                                end = start + space_break + 1

                    chunk_text = text[start:end]

                formatted_chunk = f"{doc_header}\n{chunk_text.strip()}"

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
                start = max(start + 1, end - self.chunk_overlap)

        return chunks

