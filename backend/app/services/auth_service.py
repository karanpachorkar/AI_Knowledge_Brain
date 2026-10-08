import uuid
from typing import List, Tuple
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import logger
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.repositories.rbac_repository import RBACRepository
from app.repositories.tenant_repository import TenantRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import LoginRequest, TokenResponse
from app.schemas.rbac import RoleCreate
from app.schemas.tenant import TenantCreate
from app.schemas.user import UserCreate, UserRegistration, UserResponse


class AuthService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.tenant_repo = TenantRepository(session)
        self.user_repo = UserRepository(session)
        self.rbac_repo = RBACRepository(session)

    async def register_tenant_and_admin(self, reg: UserRegistration) -> Tuple[User, TokenResponse]:
        """Registers a new tenant along with an initial Tenant Admin user."""
        # 1. Check if tenant slug already exists
        existing_tenant = await self.tenant_repo.get_by_slug(reg.tenant_slug)
        if existing_tenant:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tenant with slug '{reg.tenant_slug}' already exists."
            )

        # 2. Create Tenant
        tenant = await self.tenant_repo.create(
            TenantCreate(name=reg.tenant_name, slug=reg.tenant_slug)
        )

        # 3. Seed Permissions & Create Tenant Admin Role
        perms = await self.rbac_repo.seed_permissions()
        perm_ids = [p.id for p in perms]

        admin_role = await self.rbac_repo.create_role(
            tenant_id=tenant.id,
            role_in=RoleCreate(
                name="Tenant Admin",
                description="Full administrative access to tenant resources",
                permission_ids=perm_ids
            )
        )

        # 4. Check if admin email already exists within tenant
        existing_user = await self.user_repo.get_by_email(reg.admin_email, tenant_id=tenant.id)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists."
            )

        # 5. Create Admin User
        hashed_pw = hash_password(reg.admin_password)
        created_user = await self.user_repo.create(
            tenant_id=tenant.id,
            user_in=UserCreate(
                email=reg.admin_email,
                password=reg.admin_password,
                full_name=reg.admin_full_name
            ),
            hashed_password=hashed_pw,
            roles=[admin_role]
        )

        await self.session.commit()

        # Re-fetch user with relations
        fetched_user = await self.user_repo.get_by_id(created_user.id)
        if not fetched_user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve created user profile."
            )
        tokens = self.generate_tokens(fetched_user)

        logger.info("Successfully registered new tenant and admin", tenant_id=str(tenant.id), user_id=str(fetched_user.id))
        return fetched_user, tokens

    async def login(self, login_req: LoginRequest) -> Tuple[User, TokenResponse]:
        """Authenticates user credentials and returns tokens."""
        # Optional tenant resolution
        tenant_id = None
        if login_req.tenant_slug:
            tenant = await self.tenant_repo.get_by_slug(login_req.tenant_slug)
            if not tenant:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid credentials or tenant not found."
                )
            tenant_id = tenant.id

        user = await self.user_repo.get_by_email(login_req.email, tenant_id=tenant_id)
        if not user or not verify_password(login_req.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password."
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is deactivated."
            )

        tokens = self.generate_tokens(user)
        logger.info("Successful user login", user_id=str(user.id), tenant_id=str(user.tenant_id))
        return user, tokens

    def generate_tokens(self, user: User) -> TokenResponse:
        roles = [r.name for r in user.roles]
        permissions = list({p.name for r in user.roles for p in r.permissions})

        access_token = create_access_token(
            subject=user.id,
            tenant_id=user.tenant_id,
            roles=roles,
            permissions=permissions
        )
        refresh_token = create_refresh_token(
            subject=user.id,
            tenant_id=user.tenant_id
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )

    async def refresh_access_token(self, refresh_token_str: str) -> TokenResponse:
        payload = decode_token(refresh_token_str)
        if not payload or payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token."
            )

        user_id = uuid.UUID(payload["sub"])
        user = await self.user_repo.get_by_id(user_id)
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User inactive or not found."
            )

        return self.generate_tokens(user)

    @staticmethod
    def format_user_response(user: User) -> UserResponse:
        permissions = list({p.name for r in user.roles for p in r.permissions})
        res = UserResponse.model_validate(user)
        res.permissions = permissions
        return res
