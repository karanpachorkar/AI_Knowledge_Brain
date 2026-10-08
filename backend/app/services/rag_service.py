import json
import uuid
from typing import AsyncGenerator, Dict, List, Optional, Tuple
import httpx
from app.core.config import settings
from app.core.logging import logger
from app.schemas.chat import Citation
from app.services.retrieval_service import RetrievalCandidate, RetrievalService


from app.services.model_gateway import ModelGatewayService


class RAGService:
    UNGROUNDED_REFUSAL = "I am sorry, but I do not have sufficient relevant information in the authorized knowledge bases to answer your question."

    def __init__(self):
        self.retrieval_service = RetrievalService()
        self.gateway = ModelGatewayService()

    async def generate_rag_response(
        self,
        query: str,
        tenant_id: uuid.UUID,
        workspace_id: uuid.UUID,
        knowledge_base_id: Optional[uuid.UUID] = None,
        strict_grounding: bool = True,
        top_k: int = 5
    ) -> Tuple[str, List[Citation], bool]:
        """Executes full RAG workflow: Hybrid retrieval -> Grounding verification -> Context assembly -> LLM generation -> Citation mapping."""
        # 1. Execute Permission-Aware Hybrid Retrieval
        candidates = await self.retrieval_service.hybrid_search(
            query=query,
            tenant_id=tenant_id,
            workspace_id=workspace_id,
            knowledge_base_id=knowledge_base_id,
            limit=top_k
        )

        # 2. Grounding & Relevance Verification
        is_grounded = len(candidates) > 0 and candidates[0].fused_score > 0.05

        if not is_grounded and strict_grounding:
            logger.info("Ungrounded query detected, returning standard refusal", query=query, tenant_id=str(tenant_id))
            return self.UNGROUNDED_REFUSAL, [], False

        if not candidates:
            return self.UNGROUNDED_REFUSAL, [], False

        # 3. Assemble Context & Citations
        context_blocks: List[str] = []
        citations: List[Citation] = []

        for idx, cand in enumerate(candidates, start=1):
            doc_title = cand.metadata.get("document_title") or "Document"
            sec_title = cand.section_title or "Overview"
            pg_num = cand.page_number or 1

            context_blocks.append(
                f"[Source {idx}] Document: '{doc_title}' | Section: '{sec_title}' | Page: {pg_num}\nContent: {cand.content}"
            )

            citations.append(
                Citation(
                    document_id=cand.document_id,
                    document_title=doc_title,
                    version_id=cand.document_version_id,
                    chunk_id=cand.chunk_id,
                    section_title=sec_title,
                    page_number=pg_num,
                    snippet=cand.content[:200],
                    relevance_score=cand.fused_score
                )
            )

        context_str = "\n\n".join(context_blocks)
        system_prompt = (
            "You are an enterprise AI assistant. Answer the user prompt strictly using the provided context information. "
            "Cite sources in your text using [Source X] notation where X is the source number. "
            "If the context does not contain enough information to answer, state clearly that you do not have enough information."
        )

        full_prompt = f"System: {system_prompt}\n\nContext:\n{context_str}\n\nUser Prompt: {query}\n\nAnswer:"

        # 4. Generate Answer via Model Gateway
        answer = await self._call_llm(full_prompt, candidates)
        return answer, citations, True

    async def stream_rag_response(
        self,
        query: str,
        tenant_id: uuid.UUID,
        workspace_id: uuid.UUID,
        knowledge_base_id: Optional[uuid.UUID] = None,
        strict_grounding: bool = True,
        top_k: int = 5
    ) -> AsyncGenerator[str, None]:
        """Streams RAG response tokens via SSE chunks followed by final citation payload."""
        answer, citations, is_grounded = await self.generate_rag_response(
            query=query,
            tenant_id=tenant_id,
            workspace_id=workspace_id,
            knowledge_base_id=knowledge_base_id,
            strict_grounding=strict_grounding,
            top_k=top_k
        )

        # Stream answer in simulated/tokenized chunks
        words = answer.split(" ")
        for i in range(0, len(words), 3):
            chunk_text = " ".join(words[i:i+3]) + (" " if i + 3 < len(words) else "")
            data = {"type": "token", "content": chunk_text}
            yield f"data: {json.dumps(data)}\n\n"

        # Stream final citations & metadata event
        citation_payload = [c.model_dump() for c in citations]
        meta_data = {
            "type": "done",
            "is_grounded": is_grounded,
            "citations": citation_payload
        }
        yield f"data: {json.dumps(meta_data)}\n\n"

    async def _call_llm(self, prompt: str, candidates: List[RetrievalCandidate]) -> str:
        """Invokes Model Gateway for text generation with fallback to grounded summary synthesis."""
        try:
            answer = await self.gateway.generate_chat(prompt)
            if answer and not answer.startswith("[Synthesized Response]"):
                return answer
        except Exception as e:
            logger.warning("Model Gateway LLM warning, using grounded synthesis", error=str(e))

        # Grounded fallback synthesizer for offline execution/testing
        top_candidate = candidates[0]
        doc_title = top_candidate.metadata.get("document_title") or "Document"
        return f"Based on [Source 1] ({doc_title}): {top_candidate.content}"
