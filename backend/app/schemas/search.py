import uuid
from typing import List, Optional
from pydantic import BaseModel, Field
from app.services.retrieval_service import RetrievalCandidate


class SearchQueryRequest(BaseModel):
    query: str = Field(..., min_length=2, description="Search query string")
    workspace_id: Optional[uuid.UUID] = Field(None, description="Optional workspace scope filter")
    knowledge_base_id: Optional[uuid.UUID] = Field(None, description="Optional knowledge base scope filter")
    limit: int = Field(5, ge=1, le=50, description="Maximum number of candidate chunks to retrieve")


class SearchQueryResponse(BaseModel):
    query: str
    total_results: int
    results: List[RetrievalCandidate]
