from typing import Optional
from redis.asyncio import Redis
from app.core.config import settings
from app.core.logging import logger

redis_client: Optional[Redis] = None


async def init_redis() -> Optional[Redis]:
    global redis_client
    try:
        redis_client = Redis.from_url(
            settings.computed_redis_url,
            encoding="utf-8",
            decode_responses=True,
            socket_timeout=5.0
        )
        await redis_client.ping()
        logger.info("Successfully connected to Redis cache")
        return redis_client
    except Exception as e:
        logger.warning("Redis initialization warning", error=str(e))
        redis_client = None
        return None


async def close_redis():
    global redis_client
    if redis_client:
        await redis_client.aclose()
        logger.info("Closed Redis connection pool")


async def check_redis_connection() -> bool:
    try:
        if redis_client:
            return await redis_client.ping()
        # Fallback test connection if global client not initialized yet
        temp_client = Redis.from_url(
            settings.computed_redis_url,
            encoding="utf-8",
            decode_responses=True,
            socket_timeout=2.0
        )
        res = await temp_client.ping()
        await temp_client.aclose()
        return res
    except Exception as e:
        logger.warning("Redis healthcheck failed", error=str(e))
        return False
