from abc import ABC, abstractmethod
from enum import Enum
from typing import AsyncGenerator, Dict, List, Optional
from pydantic import BaseModel


class ProviderCapability(str, Enum):
    CHAT_GENERATION = "chat_generation"
    EMBEDDING = "embedding"
    RERANKING = "reranking"
    VISION = "vision"
    OCR = "ocr"


class RerankResult(BaseModel):
    index: int
    score: float
    document_text: str


class LLMProvider(ABC):
    @abstractmethod
    async def generate_response(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Generates a text completion."""
        pass

    @abstractmethod
    async def stream_response(self, prompt: str, system_prompt: Optional[str] = None) -> AsyncGenerator[str, None]:
        """Streams text completion tokens."""
        pass


class RerankerProvider(ABC):
    @abstractmethod
    async def rerank(self, query: str, documents: List[str], top_k: int = 5) -> List[RerankResult]:
        """Scores and re-ranks candidate document texts relative to query."""
        pass


class VisionProvider(ABC):
    @abstractmethod
    async def analyze_image(self, image_bytes: bytes, prompt: str) -> str:
        """Analyzes image content with a visual prompt."""
        pass


class OCRProvider(ABC):
    @abstractmethod
    async def extract_text(self, image_bytes: bytes, mime_type: str = "image/png") -> str:
        """Extracts plain text from document images."""
        pass
