import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app


@pytest.mark.asyncio
async def test_liveness_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "api" in data["components"]
        assert data["components"]["api"]["status"] == "healthy"


@pytest.mark.asyncio
async def test_readiness_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/readiness")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["healthy", "unhealthy", "degraded"]
        assert "database" in data["components"]
        assert "cache" in data["components"]


@pytest.mark.asyncio
async def test_root_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Generic Enterprise AI Knowledge Platform"
        assert data["version"] == "0.1.0"
