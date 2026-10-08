from typing import List
from app.core.logging import logger
from app.domain.chunking.chunker import DocumentChunk
from app.infrastructure.embeddings.ollama_provider import OllamaEmbeddingProvider
from app.infrastructure.search.opensearch_provider import OpenSearchProvider
from app.infrastructure.vector.qdrant_provider import QdrantVectorProvider


class IndexingService:
    def __init__(self):
        self.embedding_provider = OllamaEmbeddingProvider()
        self.vector_provider = QdrantVectorProvider()
        self.search_provider = OpenSearchProvider()

    async def index_chunks(self, chunks: List[DocumentChunk]) -> bool:
        """Indexes document chunks into Qdrant vector store and OpenSearch keyword engine."""
        if not chunks:
            return True

        texts = [chunk.content for chunk in chunks]
        embeddings = await self.embedding_provider.embed_documents(texts)

        # 1. Upsert into Qdrant Vector Engine
        await self.vector_provider.upsert_chunks(chunks, embeddings)

        # 2. Index into OpenSearch BM25 Engine
        await self.search_provider.index_chunks(chunks)

        logger.info("Hybrid indexing completed successfully", chunk_count=len(chunks))
        return True
