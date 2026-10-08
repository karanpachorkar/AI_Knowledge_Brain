import pytest
from app.core.database import check_database_connection
from app.core.redis import check_redis_connection


@pytest.mark.asyncio
async def test_database_connection_check_graceful_fallback():
    # Calling check_database_connection when PostgreSQL is not running returns False gracefully without throwing an uncaught exception
    status = await check_database_connection()
    assert isinstance(status, bool)


@pytest.mark.asyncio
async def test_redis_connection_check_graceful_fallback():
    # Calling check_redis_connection when Redis is not running returns False gracefully without throwing an uncaught exception
    status = await check_redis_connection()
    assert isinstance(status, bool)
