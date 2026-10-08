import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_tenant_registration_and_login_flow(async_client: AsyncClient):
    # 1. Register Tenant and Admin
    reg_payload = {
        "tenant_name": "Glatt Pharma Inc",
        "tenant_slug": "glatt-pharma",
        "admin_email": "admin@glatt-pharma.com",
        "admin_password": "SecurePassword123!",
        "admin_full_name": "Glatt System Admin"
    }
    reg_response = await async_client.post("/api/v1/auth/register", json=reg_payload)
    assert reg_response.status_code == 201
    user_data = reg_response.json()
    assert user_data["email"] == "admin@glatt-pharma.com"
    assert user_data["tenant"]["slug"] == "glatt-pharma"
    assert "user.manage" in user_data["permissions"]

    # 2. Login as Admin
    login_payload = {
        "email": "admin@glatt-pharma.com",
        "password": "SecurePassword123!",
        "tenant_slug": "glatt-pharma"
    }
    login_response = await async_client.post("/api/v1/auth/login", json=login_payload)
    assert login_response.status_code == 200
    token_data = login_response.json()
    assert "access_token" in token_data
    assert "refresh_token" in token_data
    access_token = token_data["access_token"]

    # 3. Access Protected /auth/me Endpoint
    headers = {"Authorization": f"Bearer {access_token}"}
    me_response = await async_client.get("/api/v1/auth/me", headers=headers)
    assert me_response.status_code == 200
    profile = me_response.json()
    assert profile["email"] == "admin@glatt-pharma.com"

    # 4. Refresh Token
    refresh_payload = {"refresh_token": token_data["refresh_token"]}
    refresh_response = await async_client.post("/api/v1/auth/refresh", json=refresh_payload)
    assert refresh_response.status_code == 200
    new_tokens = refresh_response.json()
    assert "access_token" in new_tokens


@pytest.mark.asyncio
async def test_invalid_login_rejection(async_client: AsyncClient):
    login_payload = {
        "email": "nonexistent@example.com",
        "password": "WrongPassword!"
    }
    response = await async_client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == 401
