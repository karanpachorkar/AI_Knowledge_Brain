import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class Citation(BaseModel):
    document_id: str
    document_title: Optional[str] = None
    version_id: str
    chunk_id: str
    section_title: Optional[str] = None
    page_number: Optional[int] = None
    snippet: str
    relevance_score: float = 0.0


class ChatRequest(BaseModel):
    workspace_id: uuid.UUID
    knowledge_base_id: Optional[uuid.UUID] = None
    conversation_id: Optional[uuid.UUID] = None
    message: str = Field(..., min_length=1, description="User prompt/question")
    strict_grounding: bool = Field(True, description="Strictly refuse ungrounded questions if true")


class ChatResponse(BaseModel):
    conversation_id: uuid.UUID
    message_id: uuid.UUID
    answer: str
    citations: List[Citation] = Field(default_factory=list)
    is_grounded: bool = True


class MessageResponse(BaseModel):
    id: uuid.UUID
    conversation_id: uuid.UUID
    tenant_id: uuid.UUID
    role: str
    content: str
    citations: List[Citation] = Field(default_factory=list)
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversationResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    workspace_id: uuid.UUID
    user_id: uuid.UUID
    title: str
    created_at: datetime
    messages: List[MessageResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
