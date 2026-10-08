from fastapi import APIRouter, status
from app.core.config import settings
from app.core.database import check_database_connection
from app.core.redis import check_redis_connection
from app.schemas.health import ComponentHealth, HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse, status_code=status.HTTP_200_OK)
async def get_liveness_health():
    """Liveness probe: Checks if the API process is alive and responsive."""
    return HealthResponse(
        status="healthy",
        environment=settings.APPLICATION_ENV,
        version="0.1.0",
        components={
            "api": ComponentHealth(status="healthy", details="FastAPI server running")
        }
    )


@router.get("/readiness", response_model=HealthResponse)
async def get_readiness_health():
    """Readiness probe: Validates database, redis, and system dependencies."""
    db_healthy = await check_database_connection()
    redis_healthy = await check_redis_connection()

    components = {
        "api": ComponentHealth(status="healthy", details="FastAPI server running"),
        "database": ComponentHealth(
            status="healthy" if db_healthy else "unhealthy",
            details="PostgreSQL connection operational" if db_healthy else "PostgreSQL connection failed"
        ),
        "cache": ComponentHealth(
            status="healthy" if redis_healthy else "degraded",
            details="Redis connection operational" if redis_healthy else "Redis connection unavailable (operating without cache)"
        )
    }

    # Overall system status determination
    if not db_healthy:
        overall_status = "unhealthy"
    elif not redis_healthy:
        overall_status = "degraded"
    else:
        overall_status = "healthy"

    return HealthResponse(
        status=overall_status,
        environment=settings.APPLICATION_ENV,
        version="0.1.0",
        components=components
    )
