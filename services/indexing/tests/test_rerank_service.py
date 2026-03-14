"""Tests for RerankService."""

from app.services.rerank import RerankService


def test_rerank_orders_by_relevance():
    """Rerank should order docs by query relevance, not original score."""
    reranker = RerankService()
    query = "error: redis connection failed"
    # "dns failure" is first but less relevant; "redis timeout" is second but more relevant
    docs = [
        {"id": "2", "content": "dns failure", "score": 0.9},
        {"id": "1", "content": "redis timeout", "score": 0.1},
    ]
    ranked = reranker.rerank(query, docs)
    # "redis timeout" should be ranked first since it's more relevant to a redis error
    assert ranked[0]["id"] == "1"


def test_rerank_returns_all_docs():
    """Rerank should return all documents, not drop any."""
    reranker = RerankService()
    query = "timeout"
    docs = [
        {"id": "a", "content": "connection timeout error", "score": 0.5},
        {"id": "b", "content": "dns resolution failed", "score": 0.8},
        {"id": "c", "content": "timeout on redis connection", "score": 0.3},
    ]
    ranked = reranker.rerank(query, docs)
    assert len(ranked) == 3
    returned_ids = {d["id"] for d in ranked}
    assert returned_ids == {"a", "b", "c"}


def test_rerank_empty_docs():
    """Rerank should handle empty doc list gracefully."""
    reranker = RerankService()
    ranked = reranker.rerank("anything", [])
    assert ranked == []


def test_rerank_single_doc():
    """Rerank with a single doc should return that doc."""
    reranker = RerankService()
    docs = [{"id": "1", "content": "only doc", "score": 0.5}]
    ranked = reranker.rerank("query", docs)
    assert len(ranked) == 1
    assert ranked[0]["id"] == "1"
