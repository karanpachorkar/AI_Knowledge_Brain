import uuid
from fastapi import APIRouter, Depends, status
from app.api.deps import get_current_tenant_id, require_permission
from app.models.user import User
from app.schemas.search import SearchQueryRequest, SearchQueryResponse
from app.services.retrieval_service import RetrievalService

router = APIRouter(prefix="/search")


@router.post("", response_model=SearchQueryResponse, status_code=status.HTTP_200_OK)
async def perform_permission_aware_search(
    search_req: SearchQueryRequest,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    _: User = Depends(require_permission("document.read"))
):
    """Executes permission-aware hybrid search (Dense Vector + BM25 Keyword) with score fusion."""
    retrieval_service = RetrievalService()
    candidates = await retrieval_service.hybrid_search(
        query=search_req.query,
        tenant_id=tenant_id,
        workspace_id=search_req.workspace_id,
        knowledge_base_id=search_req.knowledge_base_id,
        limit=search_req.limit
    )
    return SearchQueryResponse(
        query=search_req.query,
        total_results=len(candidates),
        results=candidates
    )
