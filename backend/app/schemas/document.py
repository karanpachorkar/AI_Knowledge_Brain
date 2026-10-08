import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.document_type import DocumentTypeResponse


class DocumentVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_id: uuid.UUID
    version_number: int
    file_name: str
    file_size: int
    mime_type: str
    checksum: str
    storage_key: str
    status: str
    uploaded_by_user_id: uuid.UUID
    metadata_json: Optional[dict] = None
    created_at: datetime


class DocumentACLResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_id: uuid.UUID
    role_id: Optional[uuid.UUID] = None
    user_id: Optional[uuid.UUID] = None
    permission_level: str


class DocumentCreate(BaseModel):
    workspace_id: uuid.UUID
    knowledge_base_id: uuid.UUID
    document_type_id: Optional[uuid.UUID] = None
    title: str = Field(..., min_length=2, max_length=255)
    description: Optional[str] = Field(None, max_length=500)


class DocumentVersionCreate(BaseModel):
    file_name: str
    file_size: int
    mime_type: str
    checksum: str
    storage_key: str
    metadata_json: Optional[dict] = Field(default_factory=dict)


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    workspace_id: uuid.UUID
    knowledge_base_id: uuid.UUID
    document_type_id: Optional[uuid.UUID] = None
    title: str
    description: Optional[str] = None
    created_by_user_id: uuid.UUID
    document_type: Optional[DocumentTypeResponse] = None
    versions: List[DocumentVersionResponse] = []
    acls: List[DocumentACLResponse] = []
    created_at: datetime
    updated_at: datetime
