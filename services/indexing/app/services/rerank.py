"""Rerank service for re-ordering search results by query relevance."""

from typing import TypedDict


class RerankDocument(TypedDict):
    id: str
    content: str
    score: float


class RerankService:
    """Re-ranks search results by query relevance.

    Stub implementation uses keyword overlap scoring.
    Will be replaced with a model-based reranker (e.g. BAAI/bge-reranker-base)
    when wired into the search pipeline.
    """

    def rerank(self, query: str, docs: list[RerankDocument]) -> list[RerankDocument]:
        """Re-rank documents by relevance to query.

        Args:
            query: The search query string.
            docs: List of document dicts, each with at least 'id' and 'content'.

        Returns:
            Documents re-ordered by descending relevance score.
        """
        if not docs:
            return []

        query_terms = set(query.lower().split())

        scored: list[tuple[int, RerankDocument]] = []
        for doc in docs:
            content_terms = set(doc["content"].lower().split())
            overlap = len(query_terms & content_terms)
            scored.append((overlap, doc))

        # Sort by overlap descending; stable sort preserves original order for ties
        scored.sort(key=lambda x: x[0], reverse=True)
        return [doc for _, doc in scored]
