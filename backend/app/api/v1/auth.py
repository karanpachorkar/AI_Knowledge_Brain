from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.auth import LoginRequest, RefreshTokenRequest, TokenResponse
from app.schemas.user import UserRegistration, UserResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth")


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_tenant(
    reg_data: UserRegistration,
    db: AsyncSession = Depends(get_db)
):
    """Registers a new organization/tenant along with its initial Tenant Admin."""
    auth_service = AuthService(db)
    user, _ = await auth_service.register_tenant_and_admin(reg_data)
    return auth_service.format_user_response(user)


@router.post("/login", response_model=TokenResponse)
async def login(
    login_data: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """Authenticates user credentials and issues access & refresh JWT tokens."""
    auth_service = AuthService(db)
    _, tokens = await auth_service.login(login_data)
    return tokens


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    refresh_data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db)
):
    """Refreshes expired access token using a valid refresh token."""
    auth_service = AuthService(db)
    return await auth_service.refresh_access_token(refresh_data.refresh_token)


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_user)
):
    """Retrieves profile, roles, and permissions of currently authenticated user."""
    return AuthService.format_user_response(current_user)


@router.post("/demo-token", response_model=TokenResponse)
async def get_demo_token(
    db: AsyncSession = Depends(get_db)
):
    """Issues a demo access token for seamless UI authentication."""
    auth_service = AuthService(db)
    user_repo = UserRepository(db)
    users = await user_repo.list_all(skip=0, limit=1)
    if users:
        user = users[0]
    else:
        user, _ = await auth_service.register_tenant_and_admin(
            UserRegistration(
                tenant_name="Default Organization",
                tenant_slug="default-org",
                admin_email="admin@enterprise.ai",
                admin_password="AdminPassword123!",
                admin_full_name="Default Admin"
            )
        )
    return auth_service.generate_tokens(user)
