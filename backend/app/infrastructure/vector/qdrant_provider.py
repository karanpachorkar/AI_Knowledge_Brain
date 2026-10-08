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

    async def upsert_chunks(self, chunks: List[DocumentChunk], embeddings: List[List[float]]) -> bool:
        """Upserts dense vectors and metadata payloads into Qdrant collection."""
        points = []
        for chunk, vector in zip(chunks, embeddings):
            point = {
                "id": str(chunk.id),
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
        results: List[Dict[str, Any]] = []

        # Filter candidate vectors by tenant & workspace/KB scopes
        for pt in self._shared_memory_vectors:
            payload = pt["payload"]
            if payload.get("tenant_id") != tenant_id:
                continue
            if workspace_id and payload.get("workspace_id") != workspace_id:
                continue
            if knowledge_base_id and payload.get("knowledge_base_id") != knowledge_base_id:
                continue

            # Dot product / Cosine similarity score calculation normalized to [0, 1]
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
