import json
import re
import uuid
from typing import AsyncGenerator, List, Optional, Tuple

from app.core.logging import logger
from app.schemas.chat import Citation
from app.services.rag_service import RAGService
from app.services.retrieval_service import RetrievalCandidate, RetrievalService


class AgenticRAGService:
    """Bounded orchestration layer for complex RAG questions."""

    MAX_ITERATIONS = 3
    MAX_SUBQUERIES = 4
    COMPLEX_TERMS = (
        "compare", "comparison", "difference", "differences", "versus", " vs ",
        "summarize all", "across", "multiple documents", "all documents",
        "step by step", "why and how", "combine", "analyze"
    )

    def __init__(self):
        self.rag_service = RAGService()
        self.retrieval_service = RetrievalService()

    @classmethod
    def is_complex_query(cls, query: str) -> bool:
        normalized = f" {(query or '').strip().lower()} "
        return any(term in normalized for term in cls.COMPLEX_TERMS)

    async def generate_rag_response(
        self,
        query: str,
        tenant_id: uuid.UUID,
        workspace_id: uuid.UUID,
        knowledge_base_id: Optional[uuid.UUID] = None,
        strict_grounding: bool = True,
    ) -> Tuple[str, List[Citation], bool]:
        if not self.is_complex_query(query):
            return await self.rag_service.generate_rag_response(
                query=query,
                tenant_id=tenant_id,
                workspace_id=workspace_id,
                knowledge_base_id=knowledge_base_id,
                strict_grounding=strict_grounding,
            )

        subqueries = self._build_subqueries(query)
        candidates: List[RetrievalCandidate] = []
        seen_chunks = set()

        for iteration in range(self.MAX_ITERATIONS):
            pending = subqueries if iteration == 0 else self._build_follow_up_queries(query, candidates)
            if not pending:
                break

            for subquery in pending[: self.MAX_SUBQUERIES]:
                results = await self.retrieval_service.hybrid_search(
                    query=subquery,
                    tenant_id=tenant_id,
                    workspace_id=workspace_id,
                    knowledge_base_id=knowledge_base_id,
                    limit=5,
                )
                for candidate in results:
                    if candidate.chunk_id not in seen_chunks:
                        candidates.append(candidate)
                        seen_chunks.add(candidate.chunk_id)

            candidates.sort(key=lambda item: item.fused_score, reverse=True)
            candidates = self.retrieval_service.deduplicate_candidates(candidates)
            if self._evidence_is_sufficient(candidates, len(subqueries)):
                break

        if not candidates or candidates[0].fused_score <= 0.05:
            if strict_grounding:
                return self.rag_service.UNGROUNDED_REFUSAL, [], False
            return await self.rag_service.generate_rag_response(
                query=query,
                tenant_id=tenant_id,
                workspace_id=workspace_id,
                knowledge_base_id=knowledge_base_id,
                strict_grounding=False,
            )

        citations = self._build_citations(candidates[:10])
        context = "\n\n".join(
            f"[Source {index}] Document: '{citation.document_title}' | "
            f"Section: '{citation.section_title}' | Page: {citation.page_number}\n"
            f"Content: {candidate.content.replace(chr(0), '')}"
            for index, (candidate, citation) in enumerate(zip(candidates[:10], citations), start=1)
        )
        prompt = (
            "You are an enterprise research assistant. Answer only the specific question asked, "
            "using only the evidence below. Keep the answer focused on the requested scope and "
            "do not continue into later or adjacent procedures merely because they appear in the "
            "same document. For comparisons, organize the answer by source and clearly identify "
            "similarities and differences. Cite factual statements with [Source X]. If evidence "
            "repeats the same error, step, or requirement across documents or chunks, merge it "
            "into one item and cite the relevant sources together; never list the same factual "
            "item repeatedly unless the details materially differ. If evidence "
            "is incomplete, say what is missing instead of inventing details. If the evidence "
            "contains clearly related information outside the requested scope, do not explain it "
            "in the main answer; optionally add one brief final sentence beginning with "
            "'Related information available:' to tell the user what else can be asked about. "
            "Do not add that sentence when there is no meaningful related information.\n\n"
            f"Evidence:\n{context}\n\nUser question: {query}\n\nAnswer:"
        )
        answer = await self.rag_service._call_llm(prompt, candidates[:10])
        logger.info(
            "Agentic RAG completed",
            query=query,
            iterations=iteration + 1,
            subquery_count=len(subqueries),
            evidence_count=len(candidates),
            tenant_id=str(tenant_id),
        )
        return answer, citations, True

    async def stream_rag_response(
        self,
        query: str,
        tenant_id: uuid.UUID,
        workspace_id: uuid.UUID,
        knowledge_base_id: Optional[uuid.UUID] = None,
        strict_grounding: bool = True,
    ) -> AsyncGenerator[str, None]:
        answer, citations, is_grounded = await self.generate_rag_response(
            query=query,
            tenant_id=tenant_id,
            workspace_id=workspace_id,
            knowledge_base_id=knowledge_base_id,
            strict_grounding=strict_grounding,
        )
        words = answer.split(" ")
        for index in range(0, len(words), 3):
            chunk = " ".join(words[index:index + 3])
            if index + 3 < len(words):
                chunk += " "
            yield f"data: {json.dumps({'type': 'token', 'content': chunk})}\n\n"
        yield f"data: {json.dumps({'type': 'done', 'is_grounded': is_grounded, 'citations': [citation.model_dump() for citation in citations]})}\n\n"

    def _build_subqueries(self, query: str) -> List[str]:
        cleaned = re.sub(r"\s+", " ", query).strip()
        queries = [cleaned]
        for part in re.split(r"\s+(?:and|versus|vs\.?)\s+", cleaned, flags=re.IGNORECASE):
            part = part.strip(" ,.?")
            if len(part.split()) >= 3 and part.lower() not in {cleaned.lower()}:
                queries.append(part)
        return list(dict.fromkeys(queries))[: self.MAX_SUBQUERIES]

    def _build_follow_up_queries(
        self,
        query: str,
        candidates: List[RetrievalCandidate],
    ) -> List[str]:
        if not candidates:
            return [query]
        sections = {
            candidate.section_title
            for candidate in candidates
            if candidate.section_title
        }
        if len(sections) < 2:
            return [f"{query} procedure details requirements warnings"]
        return []

    @staticmethod
    def _evidence_is_sufficient(
        candidates: List[RetrievalCandidate],
        expected_sources: int,
    ) -> bool:
        strong_candidates = [candidate for candidate in candidates if candidate.fused_score > 0.05]
        documents = {
            candidate.document_id for candidate in strong_candidates if candidate.document_id
        }
        return len(strong_candidates) >= expected_sources and bool(documents)

    @staticmethod
    def _build_citations(candidates: List[RetrievalCandidate]) -> List[Citation]:
        citations = []
        for candidate in candidates:
            content = candidate.content.replace("\x00", "")
            citations.append(
                Citation(
                    document_id=candidate.document_id,
                    document_title=candidate.metadata.get("document_title") or "Document",
                    version_id=candidate.document_version_id,
                    chunk_id=candidate.chunk_id,
                    section_title=candidate.section_title or "Overview",
                    page_number=candidate.page_number or 1,
                    snippet=content[:200],
                    relevance_score=candidate.fused_score,
                )
            )
        return citations
