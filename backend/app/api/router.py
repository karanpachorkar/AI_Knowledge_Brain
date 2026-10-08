from fastapi import APIRouter
from app.api.v1 import (
    audit,
    auth,
    chat,
    document_types,
    documents,
    health,
    knowledge_bases,
    models,
    roles,
    search,
    users,
    workspaces,
)

api_router = APIRouter()

# Register V1 Routers
api_router.include_router(health.router, tags=["Health"])
api_router.include_router(auth.router, tags=["Authentication"])
api_router.include_router(users.router, tags=["User Management"])
api_router.include_router(roles.router, tags=["Role & Permission Management"])
api_router.include_router(workspaces.router, tags=["Workspaces"])
api_router.include_router(knowledge_bases.router, tags=["Knowledge Bases"])
api_router.include_router(document_types.router, tags=["Document Types"])
api_router.include_router(documents.router, tags=["Documents"])
api_router.include_router(search.router, tags=["Search & Retrieval"])
api_router.include_router(chat.router, tags=["RAG Chat"])
api_router.include_router(models.router, tags=["Model Gateway"])
api_router.include_router(audit.router, tags=["Audit Logs"])
