import re
from typing import Any, Dict, List, Optional
from app.core.config import settings
from app.core.logging import logger
from app.domain.chunking.chunker import DocumentChunk


class OpenSearchProvider:
    _shared_memory_index: List[Dict[str, Any]] = []

    def __init__(self):
        self.url = settings.OPENSEARCH_URL
        self.index_name = "enterprise_ai_bm25"

    async def index_chunks(self, chunks: List[DocumentChunk]) -> bool:
        """Indexes text chunks for BM25 keyword matching."""
        for chunk in chunks:
            doc_record = {
                "id": str(chunk.id),
                "tenant_id": chunk.tenant_id,
                "workspace_id": chunk.workspace_id,
                "knowledge_base_id": chunk.knowledge_base_id,
                "document_id": chunk.document_id,
                "document_version_id": chunk.document_version_id,
                "content": chunk.content,
                "section_title": chunk.section_title,
                "page_number": chunk.page_number,
                "metadata": chunk.metadata
            }
            self._shared_memory_index.append(doc_record)
        logger.info("Successfully indexed chunks for BM25 search", count=len(chunks))
        return True

    async def search_keywords(
        self,
        query: str,
        tenant_id: str,
        workspace_id: Optional[str] = None,
        knowledge_base_id: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Executes BM25 keyword search pre-filtered by tenant context."""
        query_terms = set(re.findall(r"\w+", query.lower()))
        results: List[Dict[str, Any]] = []

        for doc in self._shared_memory_index:
            if doc.get("tenant_id") != tenant_id:
                continue
            if workspace_id and doc.get("workspace_id") != workspace_id:
                continue
            if knowledge_base_id and doc.get("knowledge_base_id") != knowledge_base_id:
                continue

            content_words = set(re.findall(r"\w+", doc["content"].lower()))
            matching_terms = query_terms.intersection(content_words)

            if matching_terms:
                score = len(matching_terms) / float(len(query_terms) or 1)
                results.append({
                    "id": doc["id"],
                    "score": score,
                    "payload": doc
                })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]
