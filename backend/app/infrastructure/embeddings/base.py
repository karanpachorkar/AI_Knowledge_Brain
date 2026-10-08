from abc import ABC, abstractmethod
from typing import List, Optional


class EmbeddingProvider(ABC):
    @abstractmethod
    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Generates dense vector embeddings for a list of document chunks."""
        pass

    @abstractmethod
    async def embed_query(self, text: str) -> List[float]:
        """Generates dense vector embedding for a search query string."""
        pass
