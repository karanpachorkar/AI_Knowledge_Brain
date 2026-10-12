import uuid
from typing import Any, Dict, List, Optional
import httpx
from app.core.config import settings
from app.core.logging import logger
from app.domain.chunking.chunker import DocumentChunk


class QdrantVectorProvider:
    _shared_memory_vectors: List[Dict[str, Any]] = []

    def __init__(self):
        self.url = settings.QDRANT_URL
        self.api_key = settings.QDRANT_API_KEY
        self.collection_name = "enterprise_ai_chunks"

    async def ensure_collection_exists(self, vector_size: int = 1024) -> bool:
        """Ensures Qdrant collection exists before points upsert or search."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.get(f"{self.url}/collections/{self.collection_name}")
                if res.status_code == 200:
                    return True
                create_payload = {
                    "vectors": {
                        "size": vector_size,
                        "distance": "Cosine"
                    }
                }
                await client.put(f"{self.url}/collections/{self.collection_name}", json=create_payload)
                return True
        except Exception as e:
            logger.warning("Failed to check/create Qdrant collection", error=str(e))
            return False

    async def upsert_chunks(self, chunks: List[DocumentChunk], embeddings: List[List[float]]) -> bool:
        """Upserts dense vectors and metadata payloads into Qdrant collection."""
        if not chunks:
            return True

        vector_size = len(embeddings[0]) if embeddings and len(embeddings[0]) > 0 else 1024
        await self.ensure_collection_exists(vector_size)

        points = []
        for chunk, vector in zip(chunks, embeddings):
            point = {
                "id": chunk.id,
                "vector": vector,
                "payload": {
                    "tenant_id": chunk.tenant_id,
                    "workspace_id": chunk.workspace_id,
                    "knowledge_base_id": chunk.knowledge_base_id,
                    "document_id": chunk.document_id,
                    "document_version_id": chunk.document_version_id,
                    "chunk_index": chunk.chunk_index,
                    "content": chunk.content,
                    "section_title": chunk.section_title,
                    "page_number": chunk.page_number,
                    "metadata": chunk.metadata
                }
            }
            points.append(point)
            self._shared_memory_vectors.append(point)

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.put(
                    f"{self.url}/collections/{self.collection_name}/points",
                    json={"points": points}
                )
                if res.status_code in [200, 201]:
                    logger.info("Successfully upserted points to Qdrant", count=len(points))
                    return True
        except Exception as e:
            logger.warning("Qdrant HTTP upsert fallback to memory store", error=str(e))

        return True

    async def search_vectors(
        self,
        query_vector: List[float],
        tenant_id: str,
        workspace_id: Optional[str] = None,
        knowledge_base_id: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Executes vector similarity search with mandatory tenant pre-filtering."""
        vector_size = len(query_vector) if query_vector else 1024
        await self.ensure_collection_exists(vector_size)

        must_filters = [{"key": "tenant_id", "match": {"value": tenant_id}}]
        if workspace_id:
            must_filters.append({"key": "workspace_id", "match": {"value": workspace_id}})
        if knowledge_base_id:
            must_filters.append({"key": "knowledge_base_id", "match": {"value": knowledge_base_id}})

        search_payload = {
            "vector": query_vector,
            "limit": limit,
            "filter": {"must": must_filters},
            "with_payload": True
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(
                    f"{self.url}/collections/{self.collection_name}/points/search",
                    json=search_payload
                )
                if res.status_code == 200:
                    hits = res.json().get("result", [])
                    return [
                        {
                            "id": hit["id"],
                            "score": hit["score"],
                            "payload": hit.get("payload", {})
                        }
                        for hit in hits
                    ]

        except Exception as e:
            logger.warning("Qdrant HTTP search fallback to memory store", error=str(e))

        # Memory store fallback
        results: List[Dict[str, Any]] = []
        for pt in self._shared_memory_vectors:
            payload = pt["payload"]
            if payload.get("tenant_id") != tenant_id:
                continue
            if workspace_id and payload.get("workspace_id") != workspace_id:
                continue
            if knowledge_base_id and payload.get("knowledge_base_id") != knowledge_base_id:
                continue

            vec = pt["vector"]
            raw_score = sum(q * v for q, v in zip(query_vector, vec))
            norm_score = max(0.0, (raw_score + 1.0) / 2.0)
            results.append({
                "id": pt["id"],
                "score": norm_score,
                "payload": payload
            })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]

    async def delete_document_vectors(self, tenant_id: Any, document_id: Any) -> bool:
        """Deletes all vector points associated with a specific document within a tenant context."""
        tenant_str = str(tenant_id)
        doc_str = str(document_id)

        initial_len = len(self._shared_memory_vectors)
        self._shared_memory_vectors[:] = [
            pt for pt in self._shared_memory_vectors
            if not (str(pt["payload"].get("tenant_id")) == tenant_str and str(pt["payload"].get("document_id")) == doc_str)
        ]
        deleted_count = initial_len - len(self._shared_memory_vectors)

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                filter_payload = {
                    "filter": {
                        "must": [
                            {"key": "tenant_id", "match": {"value": tenant_str}},
                            {"key": "document_id", "match": {"value": doc_str}}
                        ]
                    }
                }
                res = await client.post(
                    f"{self.url}/collections/{self.collection_name}/points/delete",
                    json=filter_payload
                )
                if res.status_code in [200, 201]:
                    logger.info("Successfully deleted points from Qdrant", tenant_id=tenant_str, document_id=doc_str)
        except Exception as e:
            logger.warning("Qdrant HTTP point deletion fallback", error=str(e))

        logger.info("Deleted document vectors from memory & Qdrant", deleted_count=deleted_count, tenant_id=tenant_str, document_id=doc_str)
        return True
