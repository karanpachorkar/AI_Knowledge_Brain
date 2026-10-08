import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class KnowledgeBaseBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    slug: str = Field(..., min_length=2, max_length=255)
    description: Optional[str] = Field(None, max_length=500)
    embedding_model: str = Field("bge-m3", max_length=100)
    chunk_size: int = Field(512, ge=64, le=4096)
    chunk_overlap: int = Field(64, ge=0, le=512)


class KnowledgeBaseCreate(KnowledgeBaseBase):
    workspace_id: uuid.UUID


class KnowledgeBaseUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    description: Optional[str] = Field(None, max_length=500)
    chunk_size: Optional[int] = Field(None, ge=64, le=4096)
    chunk_overlap: Optional[int] = Field(None, ge=0, le=512)


class KnowledgeBaseResponse(KnowledgeBaseBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    workspace_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
