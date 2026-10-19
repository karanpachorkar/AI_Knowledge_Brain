import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_tenant_id, get_current_user, require_permission
from app.core.database import get_db
from app.models.user import User
from app.repositories.chat_repository import ChatRepository
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    ConversationResponse,
    MessageDeleteRequest,
    MessageResponse,
)
from app.services.agentic_rag_service import AgenticRAGService
from app.services.rag_service import RAGService

router = APIRouter(prefix="/chat")


@router.post("", response_model=ChatResponse, status_code=status.HTTP_200_OK)
async def chat_completion(
    chat_req: ChatRequest,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    current_user: User = Depends(require_permission("document.read")),
    db: AsyncSession = Depends(get_db)
):
    """Executes permission-aware RAG chat query with citation tracking and anti-hallucination guardrails."""
    chat_repo = ChatRepository(db)
    rag_service = AgenticRAGService()

    # 1. Get or Create Conversation
    conversation = None
    if chat_req.conversation_id:
        conversation = await chat_repo.get_conversation_by_id(chat_req.conversation_id, tenant_id, current_user.id)
        if not conversation:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found.")
        chat_req.workspace_id = conversation.workspace_id
    else:
        title = chat_req.message[:50] + ("..." if len(chat_req.message) > 50 else "")
        from app.repositories.workspace_repository import WorkspaceRepository
        from app.schemas.workspace import WorkspaceCreate

        ws_repo = WorkspaceRepository(db)
        ws = await ws_repo.get_by_id(chat_req.workspace_id, tenant_id)
        if not ws:
            workspaces = await ws_repo.list_by_tenant(tenant_id)
            if workspaces:
                ws = workspaces[0]
            else:
                ws = await ws_repo.create(
                    tenant_id=tenant_id,
                    ws_in=WorkspaceCreate(
                        name="Default Workspace",
                        slug="default-workspace",
                        description="Default Workspace"
                    )
                )
            chat_req.workspace_id = ws.id

        conversation = await chat_repo.create_conversation(
            tenant_id=tenant_id,
            workspace_id=chat_req.workspace_id,
            user_id=current_user.id,
            title=title
        )

    # 2. Save User Message
    await chat_repo.create_message(
        conversation_id=conversation.id,
        tenant_id=tenant_id,
        role="user",
        content=chat_req.message
    )

    # 3. Generate RAG Response & Citations
    answer, citations, is_grounded = await rag_service.generate_rag_response(
        query=chat_req.message,
        tenant_id=tenant_id,
        workspace_id=chat_req.workspace_id,
        knowledge_base_id=chat_req.knowledge_base_id,
        strict_grounding=chat_req.strict_grounding
    )

    # 4. Save Assistant Message
    citations_json = {"citations": [c.model_dump() for c in citations]}
    asst_msg = await chat_repo.create_message(
        conversation_id=conversation.id,
        tenant_id=tenant_id,
        role="assistant",
        content=answer,
        citations_json=citations_json,
        metadata_json={"is_grounded": is_grounded}
    )

    await db.commit()

    return ChatResponse(
        conversation_id=conversation.id,
        message_id=asst_msg.id,
        answer=answer,
        citations=citations,
        is_grounded=is_grounded
    )


@router.post("/stream", status_code=status.HTTP_200_OK)
async def chat_stream(
    chat_req: ChatRequest,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    _: User = Depends(require_permission("document.read")),
):
    """Server-Sent Events (SSE) streaming RAG response endpoint."""
    rag_service = AgenticRAGService()
    generator = rag_service.stream_rag_response(
        query=chat_req.message,
        tenant_id=tenant_id,
        workspace_id=chat_req.workspace_id,
        knowledge_base_id=chat_req.knowledge_base_id,
        strict_grounding=chat_req.strict_grounding
    )
    return StreamingResponse(generator, media_type="text/event-stream")


@router.get("/conversations", response_model=List[ConversationResponse])
async def list_conversations(
    workspace_id: Optional[uuid.UUID] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Lists user's chat conversations."""
    chat_repo = ChatRepository(db)
    return await chat_repo.list_user_conversations(
        tenant_id=tenant_id,
        user_id=current_user.id,
        workspace_id=workspace_id,
        skip=skip,
        limit=limit
    )


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieves detailed conversation history including messages and citations."""
    chat_repo = ChatRepository(db)
    conv = await chat_repo.get_conversation_by_id(conversation_id, tenant_id, current_user.id)
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found.")
    return conv


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Deletes one user-owned conversation and all of its messages."""
    chat_repo = ChatRepository(db)
    deleted = await chat_repo.delete_conversation(
        conversation_id=conversation_id,
        tenant_id=tenant_id,
        user_id=current_user.id,
    )
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found.")
    await db.commit()


@router.delete("/conversations/{conversation_id}/messages/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_message(
    conversation_id: uuid.UUID,
    message_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Deletes one message from a user-owned conversation."""
    chat_repo = ChatRepository(db)
    deleted = await chat_repo.delete_message(
        message_id=message_id,
        conversation_id=conversation_id,
        tenant_id=tenant_id,
        user_id=current_user.id,
    )
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found.")
    await db.commit()


@router.delete(
    "/conversations/{conversation_id}/messages",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_messages(
    conversation_id: uuid.UUID,
    request: MessageDeleteRequest,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Deletes selected messages, or all messages when message_ids is empty."""
    chat_repo = ChatRepository(db)
    conversation = await chat_repo.get_conversation_by_id(
        conversation_id, tenant_id, current_user.id
    )
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found.")
    await chat_repo.delete_messages(
        conversation_id=conversation_id,
        tenant_id=tenant_id,
        user_id=current_user.id,
        message_ids=request.message_ids or None,
    )
    await db.commit()
