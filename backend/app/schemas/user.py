import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from app.schemas.rbac import RoleResponse
from app.schemas.tenant import TenantResponse


class UserBase(BaseModel):
    email: EmailStr = Field(..., description="User corporate email address")
    full_name: Optional[str] = Field(None, max_length=255)


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, description="Plaintext password")
    role_ids: Optional[List[uuid.UUID]] = Field(default_factory=list)


class UserRegistration(BaseModel):
    tenant_name: str = Field(..., min_length=2, max_length=255)
    tenant_slug: str = Field(..., min_length=2, max_length=255)
    admin_email: EmailStr
    admin_password: str = Field(..., min_length=8)
    admin_full_name: Optional[str] = None


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    password: Optional[str] = Field(None, min_length=8)
    is_active: Optional[bool] = None
    role_ids: Optional[List[uuid.UUID]] = None


class UserResponse(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    is_active: bool
    is_superuser: bool
    tenant: Optional[TenantResponse] = None
    roles: List[RoleResponse] = []
    permissions: List[str] = []
    created_at: datetime
    updated_at: datetime
