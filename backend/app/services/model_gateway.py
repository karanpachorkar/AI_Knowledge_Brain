from typing import AsyncGenerator, Dict, List, Optional
from pydantic import BaseModel
from app.core.config import settings
from app.core.logging import logger
from app.infrastructure.providers.base import (
    LLMProvider,
    OCRProvider,
    ProviderCapability,
    RerankerProvider,
    RerankResult,
    VisionProvider,
)
from app.infrastructure.providers.ocr_provider import StandardOCRProvider
from app.infrastructure.providers.ollama_provider import OllamaGatewayProvider
from app.infrastructure.providers.reranker_provider import CrossEncoderRerankerProvider


class ModelStatusResponse(BaseModel):
    capability: ProviderCapability
    provider_name: str
    model_name: str
    status: str = "ONLINE"


class ModelGatewayService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ModelGatewayService, cls).__new__(cls)
            cls._instance._initialize_providers()
        return cls._instance

    def _initialize_providers(self):
        self.ollama = OllamaGatewayProvider()
        self.reranker = CrossEncoderRerankerProvider()
        self.ocr = StandardOCRProvider()

    # --- Router Methods ---
    async def generate_chat(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Routes chat generation request to primary LLM Provider."""
        return await self.ollama.generate_response(prompt, system_prompt)

    async def stream_chat(self, prompt: str, system_prompt: Optional[str] = None) -> AsyncGenerator[str, None]:
        """Routes streaming chat request to primary LLM Provider."""
        async for chunk in self.ollama.stream_response(prompt, system_prompt):
            yield chunk

    async def embed_text(self, text: str) -> List[float]:
        """Routes single query embedding request."""
        return await self.ollama.embed_query(text)

    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Routes batch document embedding request."""
        return await self.ollama.embed_documents(texts)

    async def rerank_documents(self, query: str, documents: List[str], top_k: int = 5) -> List[RerankResult]:
        """Routes candidate document reranking request."""
        return await self.reranker.rerank(query, documents, top_k=top_k)

    async def analyze_vision(self, image_bytes: bytes, prompt: str) -> str:
        """Routes visual query analysis request."""
        return await self.ollama.analyze_image(image_bytes, prompt)

    async def extract_ocr_text(self, image_bytes: bytes, mime_type: str = "image/png") -> str:
        """Routes image text OCR extraction request."""
        return await self.ocr.extract_text(image_bytes, mime_type)

    def get_model_registry(self) -> List[ModelStatusResponse]:
        """Returns registered AI models and active provider statuses."""
        return [
            ModelStatusResponse(
                capability=ProviderCapability.CHAT_GENERATION,
                provider_name="OllamaProvider",
                model_name=settings.CHAT_MODEL,
                status="ONLINE"
            ),
            ModelStatusResponse(
                capability=ProviderCapability.EMBEDDING,
                provider_name="OllamaEmbeddingProvider",
                model_name=settings.EMBEDDING_MODEL,
                status="ONLINE"
            ),
            ModelStatusResponse(
                capability=ProviderCapability.RERANKING,
                provider_name="CrossEncoderRerankerProvider",
                model_name=settings.RERANKER_MODEL,
                status="ONLINE"
            ),
            ModelStatusResponse(
                capability=ProviderCapability.VISION,
                provider_name="OllamaVisionProvider",
                model_name=settings.VISION_MODEL,
                status="ONLINE"
            ),
            ModelStatusResponse(
                capability=ProviderCapability.OCR,
                provider_name="StandardOCRProvider",
                model_name="Tesseract-OCR",
                status="ONLINE"
            ),
        ]
