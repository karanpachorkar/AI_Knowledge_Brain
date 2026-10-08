import uuid
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.chat import Conversation, Message


class ChatRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_conversation(
        self,
        tenant_id: uuid.UUID,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        title: str
    ) -> Conversation:
        conv = Conversation(
            tenant_id=tenant_id,
            workspace_id=workspace_id,
            user_id=user_id,
            title=title
        )
        self.session.add(conv)
        await self.session.flush()
        return conv

    async def get_conversation_by_id(
        self,
        conversation_id: uuid.UUID,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> Optional[Conversation]:
        stmt = (
            select(Conversation)
            .options(selectinload(Conversation.messages))
            .where(
                Conversation.id == conversation_id,
                Conversation.tenant_id == tenant_id,
                Conversation.user_id == user_id
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_user_conversations(
        self,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        workspace_id: Optional[uuid.UUID] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[Conversation]:
        stmt = (
            select(Conversation)
            .options(selectinload(Conversation.messages))
            .where(
                Conversation.tenant_id == tenant_id,
                Conversation.user_id == user_id
            )
        )
        if workspace_id:
            stmt = stmt.where(Conversation.workspace_id == workspace_id)
        stmt = stmt.order_by(Conversation.created_at.desc()).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create_message(
        self,
        conversation_id: uuid.UUID,
        tenant_id: uuid.UUID,
        role: str,
        content: str,
        citations_json: Optional[dict] = None,
        metadata_json: Optional[dict] = None
    ) -> Message:
        msg = Message(
            conversation_id=conversation_id,
            tenant_id=tenant_id,
            role=role,
            content=content,
            citations_json=citations_json,
            metadata_json=metadata_json
        )
        self.session.add(msg)
        await self.session.flush()
        return msg
