import re
from typing import List
from app.core.config import settings
from app.core.logging import logger
from app.infrastructure.providers.base import RerankerProvider, RerankResult


class CrossEncoderRerankerProvider(RerankerProvider):
    def __init__(self):
        self.model_name = settings.RERANKER_MODEL

    async def rerank(self, query: str, documents: List[str], top_k: int = 5) -> List[RerankResult]:
        """Reranks document candidates by word overlap and relevance scoring."""
        query_words = set(re.findall(r"\w+", query.lower()))
        results: List[RerankResult] = []

        for idx, doc_text in enumerate(documents):
            doc_words = set(re.findall(r"\w+", doc_text.lower()))
            overlap = len(query_words.intersection(doc_words))
            score = float(overlap) / float(len(query_words) or 1)

            results.append(
                RerankResult(
                    index=idx,
                    score=score,
                    document_text=doc_text
                )
            )

        results.sort(key=lambda r: r.score, reverse=True)
        logger.info("Reranking completed", candidate_count=len(documents), top_k=top_k)
        return results[:top_k]
