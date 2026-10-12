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
        # 0. Conversational Greeting / Intent Check
        cleaned_query = (query or "").strip().lower().rstrip("!?.").strip()
        GREETINGS = {
            "hi", "hello", "hey", "hi there", "hello there", "hey there",
            "good morning", "good afternoon", "good evening",
            "how are you", "who are you", "what can you do", "help",
            "thanks", "thank you", "bye", "goodbye"
        }
        if cleaned_query in GREETINGS:
            return (
                "Hello! I am your Enterprise AI Assistant. How can I help you today with your knowledge bases, SOPs, or enterprise documents?",
                [],
                True
            )

        # 0.1 Fetch Verified Document Inventory from Database
        doc_inventory: List[str] = []
        try:
            from app.core.database import AsyncSessionLocal
            from app.repositories.document_repository import DocumentRepository
            async with AsyncSessionLocal() as session:
                doc_repo = DocumentRepository(session)
                docs = await doc_repo.list_by_tenant(tenant_id)
                for d in docs:
                    if not workspace_id or str(d.workspace_id) == str(workspace_id):
                        ver = d.versions[0] if d.versions else None
                        fname = ver.file_name if ver else d.title
                        pg_count = ver.metadata_json.get("parsed_sections") if ver and ver.metadata_json else None
                        pg_info = f" ({pg_count} sections/pages)" if pg_count else ""
                        doc_inventory.append(f"- **{d.title}** (`{fname}`){pg_info}")
        except Exception as ex:
            logger.warning("Could not fetch document inventory from DB", error=str(ex))

        # Check for Metadata / Inventory queries
        inventory_phrases = [
            "how many document", "how many file", "list document", "list file",
            "what document", "which document", "what file", "which file",
            "show document", "all document", "available document", "how many docs"
        ]
        if any(p in cleaned_query for p in inventory_phrases):
            count = len(doc_inventory)
            if count == 0:
                answer = "There are currently no documents uploaded in this knowledge base."
            elif count == 1:
                answer = f"There is currently **1 document** in this knowledge base:\n\n{doc_inventory[0]}"
            else:
                docs_formatted = "\n".join(doc_inventory)
                answer = f"There are currently **{count} documents** in this knowledge base:\n\n{docs_formatted}"
            return answer, [], True

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
        inv_note = ""
        if doc_inventory:

            inv_note = "\nAuthorized Documents in Workspace:\n" + "\n".join(doc_inventory) + "\nNote: Multiple sources [Source 1], [Source 2], etc., may come from different pages of the SAME document. Do not mistake source snippet counts for document counts.\n"

        system_prompt = (
            "You are an enterprise AI assistant. Answer the user prompt comprehensively and accurately using the provided context information. "
            "When listing requirements, prerequisites, tables, or step-by-step procedures, extract and list ALL items from the context completely without omission. "
            "When summarizing documents or procedures, provide a well-structured executive summary covering all main sections and phases cleanly. "
            "When answering questions about images, hardware, components, or manufacturers, carefully examine any [Embedded Image / Visual Content] notes and OCR data in the context. "
            "Cite sources in your text using [Source X] notation where X is the source number. "
            "If the context does not contain enough information to answer, state clearly that you do not have enough information."
            + inv_note
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

        # Grounded fallback synthesizer for offline execution or gateway timeout
        if not candidates:
            return self.UNGROUNDED_REFUSAL
        top_candidate = candidates[0]
        doc_title = top_candidate.metadata.get("document_title") or "Document"
        highlights = "\n\n".join([f"- **{c.section_title or f'Page {c.page_number or i+1}'}**: {c.content[:220].strip()}..." for i, c in enumerate(candidates[:4])])
        return f"### Summary ({doc_title})\n\n{highlights}"
