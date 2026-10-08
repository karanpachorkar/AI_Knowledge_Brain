import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_tenant_isolation_and_rbac_enforcement(async_client: AsyncClient):
    # 1. Register Tenant A
    tenant_a_reg = {
        "tenant_name": "Company Alpha",
        "tenant_slug": "alpha-corp",
        "admin_email": "admin@alpha.com",
        "admin_password": "AlphaPassword123!"
    }
    res_a = await async_client.post("/api/v1/auth/register", json=tenant_a_reg)
    assert res_a.status_code == 201

    login_a = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "admin@alpha.com", "password": "AlphaPassword123!", "tenant_slug": "alpha-corp"}
    )
    token_a = login_a.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # 2. Register Tenant B
    tenant_b_reg = {
        "tenant_name": "Company Beta",
        "tenant_slug": "beta-corp",
        "admin_email": "admin@beta.com",
        "admin_password": "BetaPassword123!"
    }
    res_b = await async_client.post("/api/v1/auth/register", json=tenant_b_reg)
    assert res_b.status_code == 201

    login_b = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "admin@beta.com", "password": "BetaPassword123!", "tenant_slug": "beta-corp"}
    )
    token_b = login_b.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # 3. Tenant A admin lists users in Tenant A
    users_a = await async_client.get("/api/v1/users", headers=headers_a)
    assert users_a.status_code == 200
    user_list_a = users_a.json()
    assert len(user_list_a) == 1
    assert user_list_a[0]["email"] == "admin@alpha.com"

    # 4. Tenant B admin lists users in Tenant B (Isolated from Tenant A)
    users_b = await async_client.get("/api/v1/users", headers=headers_b)
    assert users_b.status_code == 200
    user_list_b = users_b.json()
    assert len(user_list_b) == 1
    assert user_list_b[0]["email"] == "admin@beta.com"

    # Tenant B list MUST NOT contain Tenant A's user
    b_emails = [u["email"] for u in user_list_b]
    assert "admin@alpha.com" not in b_emails
