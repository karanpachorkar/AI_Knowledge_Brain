import uuid
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    tenant_slug: Optional[str] = Field(None, description="Target tenant slug if user belongs to multiple tenants")


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class TokenPayload(BaseModel):
    sub: str  # user_id
    tenant_id: str
    roles: List[str] = []
    permissions: List[str] = []
    type: str  # "access" or "refresh"
    exp: Optional[int] = None
