import uuid
from typing import List, Optional
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.chat import Conversation, Message


def _remove_null_bytes(value):
    if isinstance(value, str):
        return value.replace("\x00", "")
    if isinstance(value, list):
        return [_remove_null_bytes(item) for item in value]
    if isinstance(value, dict):
        return {key: _remove_null_bytes(item) for key, item in value.items()}
    return value


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
            content=_remove_null_bytes(content),
            citations_json=_remove_null_bytes(citations_json),
            metadata_json=_remove_null_bytes(metadata_json)
        )
        self.session.add(msg)
        await self.session.flush()
        return msg

    async def delete_message(
        self,
        message_id: uuid.UUID,
        conversation_id: uuid.UUID,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> bool:
        stmt = (
            delete(Message)
            .where(
                Message.id == message_id,
                Message.conversation_id == conversation_id,
                Message.tenant_id == tenant_id,
                Message.conversation.has(
                    Conversation.user_id == user_id,
                    Conversation.tenant_id == tenant_id,
                ),
            )
        )
        result = await self.session.execute(stmt)
        return result.rowcount > 0

    async def delete_messages(
        self,
        conversation_id: uuid.UUID,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        message_ids: Optional[List[uuid.UUID]] = None,
    ) -> int:
        conditions = [
            Message.conversation_id == conversation_id,
            Message.tenant_id == tenant_id,
            Message.conversation.has(
                Conversation.user_id == user_id,
                Conversation.tenant_id == tenant_id,
            ),
        ]
        if message_ids:
            conditions.append(Message.id.in_(message_ids))
        result = await self.session.execute(delete(Message).where(*conditions))
        return result.rowcount or 0

    async def delete_conversation(
        self,
        conversation_id: uuid.UUID,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> bool:
        stmt = delete(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.tenant_id == tenant_id,
            Conversation.user_id == user_id,
        )
        result = await self.session.execute(stmt)
        return result.rowcount > 0
