"""Tests for rerank integration in hybrid search pipeline."""

from unittest.mock import AsyncMock, patch

import pytest

from app.models.requests import SearchResponse
from app.services.rerank import RerankService


# ---------------------------------------------------------------------------
# 1. SearchResponse model has rerank metadata fields
# ---------------------------------------------------------------------------


class TestSearchResponseRerankFields:
    """SearchResponse should expose reranked flag and rerank_model name."""

    def test_search_response_has_reranked_field(self):
        resp = SearchResponse(
            query="test",
            results=[],
            total=0,
            search_type="hybrid",
            reranked=True,
            rerank_model="keyword-overlap",
        )
        assert resp.reranked is True

    def test_search_response_reranked_defaults_false(self):
        resp = SearchResponse(
            query="test",
            results=[],
            total=0,
            search_type="hybrid",
        )
        assert resp.reranked is False

    def test_search_response_rerank_model_defaults_none(self):
        resp = SearchResponse(
            query="test",
            results=[],
            total=0,
            search_type="hybrid",
        )
        assert resp.rerank_model is None

    def test_search_response_rerank_model_set(self):
        resp = SearchResponse(
            query="test",
            results=[],
            total=0,
            search_type="hybrid",
            rerank_model="BAAI/bge-reranker-base",
        )
        assert resp.rerank_model == "BAAI/bge-reranker-base"


# ---------------------------------------------------------------------------
# 2. hybrid_search wires RerankService and returns reranked results
# ---------------------------------------------------------------------------


class TestHybridSearchRerank:
    """SearchService.hybrid_search should invoke RerankService after fusion."""

    @pytest.fixture
    def search_service(self):
        """Create a SearchService with mocked ES client."""
        from app.services.search import SearchService

        svc = SearchService.__new__(SearchService)
        svc.es = AsyncMock()
        svc.index = "test_index"
        svc.reranker = RerankService()
        return svc

    @pytest.mark.asyncio
    async def test_hybrid_search_reranks_results(self, search_service):
        """After score fusion, hybrid_search should rerank via RerankService."""
        # Arrange: mock semantic + keyword to return known docs
        doc_a = {
            "id": "a",
            "title": "Redis Config",
            "content": "redis connection pool setup",
            "score": 0.8,
            "source": None,
            "url": None,
            "metadata": {},
        }
        doc_b = {
            "id": "b",
            "title": "DNS Guide",
            "content": "dns lookup and resolution",
            "score": 0.9,
            "source": None,
            "url": None,
            "metadata": {},
        }

        search_service.semantic_search = AsyncMock(return_value=[doc_b, doc_a])
        search_service.keyword_search = AsyncMock(return_value=[doc_b, doc_a])

        with patch("app.services.search.settings") as settings:
            settings.rerank_enabled = True
            settings.rerank_model_name = "BAAI/bge-reranker-base"
            result = await search_service.hybrid_search(
                query="redis connection",
                query_embedding=[0.1] * 384,
                top_k=10,
            )

        # doc_a ("redis connection pool setup") should be ranked higher for
        # query "redis connection" after reranking by keyword overlap.
        assert result["results"][0]["id"] == "a"

    @pytest.mark.asyncio
    async def test_hybrid_search_returns_dict_with_rerank_metadata(self, search_service):
        """hybrid_search return value should include reranked flag and model name."""
        search_service.semantic_search = AsyncMock(return_value=[])
        search_service.keyword_search = AsyncMock(return_value=[])

        with patch("app.services.search.settings") as settings:
            settings.rerank_enabled = True
            settings.rerank_model_name = "BAAI/bge-reranker-base"
            result = await search_service.hybrid_search(
                query="anything",
                query_embedding=[0.1] * 384,
                top_k=5,
            )

        # hybrid_search should now return a dict with metadata, not just a list
        assert isinstance(result, dict)
        assert result["reranked"] is True
        assert "rerank_model" in result
        assert isinstance(result["results"], list)

    @pytest.mark.asyncio
    async def test_hybrid_search_preserves_all_docs_after_rerank(self, search_service):
        """Reranking should not drop any documents."""
        docs = [
            {
                "id": str(i),
                "title": f"Doc {i}",
                "content": f"content {i}",
                "score": 0.5,
                "source": None,
                "url": None,
                "metadata": {},
            }
            for i in range(5)
        ]
        search_service.semantic_search = AsyncMock(return_value=docs)
        search_service.keyword_search = AsyncMock(return_value=[])

        with patch("app.services.search.settings") as settings:
            settings.rerank_enabled = True
            settings.rerank_model_name = "BAAI/bge-reranker-base"
            result = await search_service.hybrid_search(
                query="content",
                query_embedding=[0.1] * 384,
                top_k=10,
            )

        assert len(result["results"]) == 5

    @pytest.mark.asyncio
    async def test_hybrid_search_rerank_model_is_default_name(self, search_service):
        search_service.semantic_search = AsyncMock(return_value=[])
        search_service.keyword_search = AsyncMock(return_value=[])

        with patch("app.services.search.settings") as settings:
            settings.rerank_enabled = True
            settings.rerank_model_name = "BAAI/bge-reranker-base"
            result = await search_service.hybrid_search(
                query="test",
                query_embedding=[0.1] * 384,
                top_k=5,
            )

        assert result["rerank_model"] == "BAAI/bge-reranker-base"

    @pytest.mark.asyncio
    async def test_hybrid_search_returns_unreranked_when_disabled(self, search_service):
        search_service.semantic_search = AsyncMock(return_value=[])
        search_service.keyword_search = AsyncMock(return_value=[])

        with patch("app.services.search.settings") as settings:
            settings.rerank_enabled = False
            settings.rerank_model_name = "BAAI/bge-reranker-base"
            result = await search_service.hybrid_search(
                query="test",
                query_embedding=[0.1] * 384,
                top_k=5,
            )

        assert result["reranked"] is False
        assert result["rerank_model"] is None
