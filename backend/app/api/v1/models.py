from typing import List
from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from pydantic import BaseModel, Field

from app.api.deps import get_current_user
from app.models.user import User
from app.services.model_gateway import ModelGatewayService, ModelStatusResponse

router = APIRouter(prefix="/models")


class RerankRequest(BaseModel):
    query: str = Field(..., min_length=1)
    documents: List[str] = Field(..., min_length=1)
    top_k: int = Field(5, ge=1)


class RerankResponse(BaseModel):
    query: str
    results: List[dict]


@router.get("", response_model=List[ModelStatusResponse])
async def list_registered_models(
    _: User = Depends(get_current_user)
):
    """Lists registered AI models, capabilities, and provider status."""
    gateway = ModelGatewayService()
    return gateway.get_model_registry()


@router.post("/rerank", response_model=RerankResponse, status_code=status.HTTP_200_OK)
async def rerank_documents(
    rerank_req: RerankRequest,
    _: User = Depends(get_current_user)
):
    """Re-ranks candidate document texts using Cross-Encoder model gateway capability."""
    gateway = ModelGatewayService()
    results = await gateway.rerank_documents(
        query=rerank_req.query,
        documents=rerank_req.documents,
        top_k=rerank_req.top_k
    )
    return RerankResponse(
        query=rerank_req.query,
        results=[r.model_dump() for r in results]
    )


@router.post("/ocr", status_code=status.HTTP_200_OK)
async def extract_ocr_from_image(
    file: UploadFile = File(...),
    _: User = Depends(get_current_user)
):
    """Extracts text from uploaded image file using Model Gateway OCR capability."""
    gateway = ModelGatewayService()
    img_bytes = await file.read()
    extracted_text = await gateway.extract_ocr_text(
        image_bytes=img_bytes,
        mime_type=file.content_type or "image/png"
    )
    return {
        "file_name": file.filename,
        "extracted_text": extracted_text
    }
