import json
import re
from typing import Any, Dict, List, Optional
import httpx
from app.core.config import settings
from app.core.logging import logger
from app.domain.chunking.chunker import DocumentChunk


class OpenSearchProvider:
    _shared_memory_index: List[Dict[str, Any]] = []

    def __init__(self):
        self.url = settings.OPENSEARCH_URL
        self.index_name = "enterprise_ai_bm25"

    async def ensure_index_exists(self) -> bool:
        """Ensures OpenSearch index exists before indexing or searching."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.get(f"{self.url}/{self.index_name}")
                if res.status_code == 200:
                    return True
                create_payload = {
                    "mappings": {
                        "properties": {
                            "tenant_id": {"type": "keyword"},
                            "workspace_id": {"type": "keyword"},
                            "knowledge_base_id": {"type": "keyword"},
                            "document_id": {"type": "keyword"},
                            "content": {"type": "text"}
                        }
                    }
                }
                await client.put(f"{self.url}/{self.index_name}", json=create_payload)
                return True
        except Exception as e:
            logger.warning("Failed to check/create OpenSearch index", error=str(e))
            return False

    async def index_chunks(self, chunks: List[DocumentChunk]) -> bool:
        """Indexes text chunks for BM25 keyword matching."""
        if not chunks:
            return True

        await self.ensure_index_exists()

        bulk_lines = []
        for chunk in chunks:
            doc_record = {
                "id": str(chunk.id),
                "tenant_id": str(chunk.tenant_id),
                "workspace_id": str(chunk.workspace_id),
                "knowledge_base_id": str(chunk.knowledge_base_id),
                "document_id": str(chunk.document_id),
                "document_version_id": str(chunk.document_version_id),
                "content": chunk.content,
                "section_title": chunk.section_title,
                "page_number": chunk.page_number,
                "metadata": chunk.metadata
            }
            self._shared_memory_index.append(doc_record)

            bulk_lines.append(json.dumps({"index": {"_index": self.index_name, "_id": str(chunk.id)}}))
            bulk_lines.append(json.dumps(doc_record))

        bulk_body = "\n".join(bulk_lines) + "\n"

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(
                    f"{self.url}/_bulk",
                    content=bulk_body,
                    headers={"Content-Type": "application/x-ndjson"}
                )
                if res.status_code in [200, 201]:
                    logger.info("Successfully indexed chunks into OpenSearch container", count=len(chunks))
                    return True
        except Exception as e:
            logger.warning("OpenSearch HTTP bulk index fallback to memory store", error=str(e))

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
        await self.ensure_index_exists()

        must_filters = [{"term": {"tenant_id": tenant_id}}]
        if workspace_id:
            must_filters.append({"term": {"workspace_id": workspace_id}})
        if knowledge_base_id:
            must_filters.append({"term": {"knowledge_base_id": knowledge_base_id}})

        search_query = {
            "size": limit,
            "query": {
                "bool": {
                    "filter": must_filters,
                    "must": [
                        {
                            "multi_match": {
                                "query": query,
                                "fields": ["content", "section_title^2", "metadata.document_title^3"]
                            }
                        }
                    ]
                }
            }
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(
                    f"{self.url}/{self.index_name}/_search",
                    json=search_query
                )
                if res.status_code == 200:
                    hits = res.json().get("hits", {}).get("hits", [])
                    return [
                        {
                            "id": hit["_id"],
                            "score": hit["_score"],
                            "payload": hit.get("_source", {})
                        }
                        for hit in hits
                    ]

        except Exception as e:
            logger.warning("OpenSearch HTTP search fallback to memory store", error=str(e))

        # Memory store fallback
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

    async def delete_document_index(self, tenant_id: Any, document_id: Any) -> bool:
        """Deletes all indexed BM25 text chunks associated with a specific document within a tenant context."""
        tenant_str = str(tenant_id)
        doc_str = str(document_id)
        initial_len = len(self._shared_memory_index)
        self._shared_memory_index[:] = [
            doc for doc in self._shared_memory_index
            if not (str(doc.get("tenant_id")) == tenant_str and str(doc.get("document_id")) == doc_str)
        ]
        deleted_count = initial_len - len(self._shared_memory_index)

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                query = {
                    "query": {
                        "bool": {
                            "must": [
                                {"term": {"tenant_id": tenant_str}},
                                {"term": {"document_id": doc_str}}
                            ]
                        }
                    }
                }
                await client.post(f"{self.url}/{self.index_name}/_delete_by_query?refresh=true", json=query)
        except Exception as e:
            logger.warning("OpenSearch HTTP delete by query fallback", error=str(e))

        logger.info("Deleted document chunks from OpenSearch index", deleted_count=deleted_count, tenant_id=tenant_str, document_id=doc_str)
        return True
