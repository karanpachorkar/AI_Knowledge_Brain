from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api.router import api_router
from app.core.config import settings
from app.core.logging import logger, setup_logging
from app.core.redis import close_redis, init_redis


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup tasks
    setup_logging()
    logger.info("Initializing Enterprise AI Knowledge Platform Backend", env=settings.APPLICATION_ENV)
    await init_redis()
    yield
    # Shutdown tasks
    logger.info("Shutting down Enterprise AI Backend services")
    await close_redis()


app = FastAPI(
    title="Generic Enterprise AI Knowledge Platform",
    description="Production-grade, generic Enterprise RAG & Knowledge Management System",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

from app.core.middleware import RequestIDMiddleware

# Request ID Middleware
app.add_middleware(RequestIDMiddleware)

# CORS Configuration
if settings.CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

import traceback

# Global Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    traceback.print_exc()
    error_str = str(exc).encode("ascii", errors="replace").decode("ascii")
    logger.error(
        "Unhandled Application Exception",
        path=request.url.path,
        error=error_str
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "An internal server error occurred.",
            "error_code": "INTERNAL_SERVER_ERROR"
        }
    )

# Mount V1 Routers
app.include_router(api_router, prefix="/api/v1")
# Expose top-level /health & /readiness endpoints
from app.api.v1.health import router as health_router
app.include_router(health_router, tags=["Health"])


@app.get("/")
async def root_info():
    return {
        "name": "Generic Enterprise AI Knowledge Platform",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
        "readiness": "/readiness"
    }
