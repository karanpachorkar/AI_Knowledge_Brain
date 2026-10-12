import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from app.infrastructure.embeddings.ollama_provider import OllamaEmbeddingProvider
from app.infrastructure.search.opensearch_provider import OpenSearchProvider
from app.infrastructure.vector.qdrant_provider import QdrantVectorProvider


class RetrievalCandidate(BaseModel):
    chunk_id: str
    content: str
    section_title: Optional[str] = None
    page_number: Optional[int] = None
    document_id: str
    document_version_id: str
    knowledge_base_id: str
    workspace_id: str
    dense_score: float = 0.0
    bm25_score: float = 0.0
    fused_score: float = 0.0
    metadata: Dict = Field(default_factory=dict)


class RetrievalService:
    def __init__(self):
        self.embedding_provider = OllamaEmbeddingProvider()
        self.vector_provider = QdrantVectorProvider()
        self.search_provider = OpenSearchProvider()

    async def hybrid_search(
        self,
        query: str,
        tenant_id: uuid.UUID,
        workspace_id: Optional[uuid.UUID] = None,
        knowledge_base_id: Optional[uuid.UUID] = None,
        limit: int = 5,
        vector_weight: float = 0.7,
        bm25_weight: float = 0.3
    ) -> List[RetrievalCandidate]:
        """Executes permission-aware hybrid search (Dense Vector + BM25 Keyword) with score fusion."""
        tenant_str = str(tenant_id)
        ws_str = str(workspace_id) if workspace_id else None
        kb_str = str(knowledge_base_id) if knowledge_base_id else None

        # 1. Generate Dense Query Embedding
        query_vector = await self.embedding_provider.embed_query(query)

        # 2. Qdrant Dense Vector Search
        vector_results = await self.vector_provider.search_vectors(
            query_vector=query_vector,
            tenant_id=tenant_str,
            workspace_id=ws_str,
            knowledge_base_id=kb_str,
            limit=limit * 2
        )

        # 2. OpenSearch BM25 Keyword Search with stop word filtering and format expansion
        lower_q = query.lower()
        stop_words = {
            "what", "does", "the", "a", "an", "is", "are", "was", "were", "of", "in", 
            "to", "for", "with", "on", "at", "from", "by", "about", "as", "into", 
            "like", "through", "after", "over", "between", "out", "against", "during", 
            "without", "before", "under", "around", "among", "it", "its", "this", 
            "that", "these", "those", "can", "you", "we", "i", "me", "my", "our", "do", "did"
        }
        tokens = [w for w in lower_q.split() if w.strip("?.,!;:\"'()[]{}") not in stop_words]
        clean_query = " ".join(tokens) if tokens else query

        if any(term in lower_q for term in ["ppt", "powerpoint", "slide", "slides", "presentation"]):
            bm25_query = f"{clean_query} slide slides pptx presentation"
        elif "pdf" in lower_q:
            bm25_query = f"{clean_query} pdf page document"
        else:
            bm25_query = clean_query

        bm25_results = await self.search_provider.search_keywords(
            query=bm25_query,
            tenant_id=tenant_str,
            workspace_id=ws_str,
            knowledge_base_id=kb_str,
            limit=limit * 2
        )

        # 4. Score Fusion (Reciprocal Rank / Weighted Normalization)
        candidate_map: Dict[str, RetrievalCandidate] = {}

        for res in vector_results:
            cid = res["id"]
            payload = res["payload"]
            candidate_map[cid] = RetrievalCandidate(
                chunk_id=cid,
                content=payload.get("content", ""),
                section_title=payload.get("section_title"),
                page_number=payload.get("page_number"),
                document_id=payload.get("document_id", ""),
                document_version_id=payload.get("document_version_id", ""),
                knowledge_base_id=payload.get("knowledge_base_id", ""),
                workspace_id=payload.get("workspace_id", ""),
                dense_score=res["score"],
                metadata=payload.get("metadata", {})
            )

        for res in bm25_results:
            cid = res["id"]
            payload = res["payload"]
            if cid in candidate_map:
                candidate_map[cid].bm25_score = res["score"]
            else:
                candidate_map[cid] = RetrievalCandidate(
                    chunk_id=cid,
                    content=payload.get("content", ""),
                    section_title=payload.get("section_title"),
                    page_number=payload.get("page_number"),
                    document_id=payload.get("document_id", ""),
                    document_version_id=payload.get("document_version_id", ""),
                    knowledge_base_id=payload.get("knowledge_base_id", ""),
                    workspace_id=payload.get("workspace_id", ""),
                    bm25_score=res["score"],
                    metadata=payload.get("metadata", {})
                )

        # Calculate Fused Score (Only positive dense cosine similarity and BM25 scores contribute)
        final_candidates: List[RetrievalCandidate] = []
        for cand in candidate_map.values():
            norm_dense = max(0.0, cand.dense_score)
            norm_bm25 = max(0.0, cand.bm25_score)
            cand.fused_score = (norm_dense * vector_weight) + (norm_bm25 * bm25_weight)
            final_candidates.append(cand)


        final_candidates.sort(key=lambda x: x.fused_score, reverse=True)
        return final_candidates[:limit]

