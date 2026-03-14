"""Tests for secondary rerank service stub.

Covers: secondary_rerank function signature, return structure,
passthrough behavior (stub), and integration hooks in agent flows.
"""

import pytest
from typing import Any, Dict, List


# ---------------------------------------------------------------------------
# secondary_rerank stub – basic contract
# ---------------------------------------------------------------------------


class TestSecondaryRerankImport:
    """secondary_rerank is importable from app.services.rerank."""

    def test_importable(self):
        from app.services.rerank import secondary_rerank

        assert callable(secondary_rerank)


class TestSecondaryRerankContract:
    """secondary_rerank stub returns documents unchanged (passthrough)."""

    async def test_returns_list(self):
        from app.services.rerank import secondary_rerank

        docs = [{"content": "fix CI", "score": 0.9}]
        result = await secondary_rerank(docs, query="CI failure")
        assert isinstance(result, list)

    async def test_passthrough_preserves_documents(self):
        from app.services.rerank import secondary_rerank

        docs = [
            {"content": "fix CI", "score": 0.9},
            {"content": "update README", "score": 0.5},
        ]
        result = await secondary_rerank(docs, query="CI failure")
        assert result == docs

    async def test_empty_documents_returns_empty(self):
        from app.services.rerank import secondary_rerank

        result = await secondary_rerank([], query="anything")
        assert result == []

    async def test_single_document_passthrough(self):
        from app.services.rerank import secondary_rerank

        docs = [{"content": "one doc", "score": 1.0}]
        result = await secondary_rerank(docs, query="test")
        assert result == docs

    async def test_preserves_document_order(self):
        from app.services.rerank import secondary_rerank

        docs = [
            {"content": "first", "score": 0.3},
            {"content": "second", "score": 0.7},
            {"content": "third", "score": 0.1},
        ]
        result = await secondary_rerank(docs, query="test")
        assert [d["content"] for d in result] == ["first", "second", "third"]

    async def test_accepts_optional_top_k(self):
        """Stub should accept top_k kwarg without error."""
        from app.services.rerank import secondary_rerank

        docs = [{"content": "a", "score": 0.5}, {"content": "b", "score": 0.3}]
        result = await secondary_rerank(docs, query="test", top_k=1)
        assert isinstance(result, list)

    async def test_accepts_optional_model_name(self):
        """Stub should accept model_name kwarg without error."""
        from app.services.rerank import secondary_rerank

        docs = [{"content": "a", "score": 0.5}]
        result = await secondary_rerank(docs, query="test", model_name="cross-encoder")
        assert isinstance(result, list)


# ---------------------------------------------------------------------------
# should_rerank helper
# ---------------------------------------------------------------------------


class TestShouldRerank:
    """should_rerank checks config to decide if reranking applies."""

    def test_importable(self):
        from app.services.rerank import should_rerank

        assert callable(should_rerank)

    def test_returns_false_when_disabled(self, monkeypatch):
        monkeypatch.setenv("SECONDARY_RERANK_ENABLED", "false")
        monkeypatch.delenv("SECONDARY_RERANK_TARGETS", raising=False)
        # Re-import to get fresh settings
        from app.services.rerank import should_rerank

        assert should_rerank("pr_risk", enabled=False, targets=[]) is False

    def test_returns_false_when_target_not_in_list(self):
        from app.services.rerank import should_rerank

        assert should_rerank("pr_risk", enabled=True, targets=["build_failure_triage"]) is False

    def test_returns_true_when_enabled_and_target_matches(self):
        from app.services.rerank import should_rerank

        assert should_rerank("pr_risk", enabled=True, targets=["pr_risk", "code_review"]) is True

    def test_returns_false_when_enabled_but_targets_empty(self):
        from app.services.rerank import should_rerank

        assert should_rerank("pr_risk", enabled=True, targets=[]) is False


# ---------------------------------------------------------------------------
# Integration: pr_risk_agent applies secondary rerank when enabled
# ---------------------------------------------------------------------------


class TestPRRiskAgentSecondaryRerank:
    """pr_risk_agent.run_pr_risk_agent applies secondary rerank when config enables it."""

    async def test_result_has_reranked_key_when_enabled(self, monkeypatch):
        """When secondary rerank is enabled for pr_risk, result should have reranked flag."""
        from unittest.mock import AsyncMock

        monkeypatch.setattr(
            "app.agents.pr_risk_agent.settings",
            type(
                "S",
                (),
                {
                    "secondary_rerank_enabled": True,
                    "secondary_rerank_targets": ["pr_risk"],
                },
            )(),
        )
        monkeypatch.setattr(
            "app.agents.pr_risk_agent.classify_risk",
            AsyncMock(return_value={"label": "high"}),
        )
        monkeypatch.setattr(
            "app.agents.pr_risk_agent.secondary_rerank",
            AsyncMock(return_value=[{"content": "reranked", "score": 0.99}]),
        )

        from app.agents.pr_risk_agent import run_pr_risk_agent

        result = await run_pr_risk_agent({"diff": "some diff"})
        assert result.get("reranked") is True

    async def test_no_reranked_key_when_disabled(self, monkeypatch):
        """When secondary rerank is disabled, result should not have reranked flag."""
        from unittest.mock import AsyncMock

        monkeypatch.setattr(
            "app.agents.pr_risk_agent.settings",
            type(
                "S",
                (),
                {
                    "secondary_rerank_enabled": False,
                    "secondary_rerank_targets": [],
                },
            )(),
        )
        monkeypatch.setattr(
            "app.agents.pr_risk_agent.classify_risk",
            AsyncMock(return_value={"label": "low"}),
        )

        from app.agents.pr_risk_agent import run_pr_risk_agent

        result = await run_pr_risk_agent({"diff": "some diff"})
        assert result.get("reranked") is not True


# ---------------------------------------------------------------------------
# Integration: code_review_flow applies secondary rerank when enabled
# ---------------------------------------------------------------------------


class TestCodeReviewFlowSecondaryRerank:
    """run_code_review applies secondary rerank when config enables it."""

    async def test_result_has_reranked_key_when_enabled(self, monkeypatch):
        """When secondary rerank is enabled for code_review, result should have reranked flag."""
        from unittest.mock import AsyncMock

        # Reset circuit breaker to avoid pollution from other tests
        import app.workflows.code_review_flow as crf
        crf._CODE_REVIEW_BREAKER.failure_count = 0
        crf._CODE_REVIEW_BREAKER.open_until = None

        monkeypatch.setattr(
            "app.workflows.code_review_flow.settings",
            type(
                "S",
                (),
                {
                    "secondary_rerank_enabled": True,
                    "secondary_rerank_targets": ["code_review"],
                },
            )(),
        )
        monkeypatch.setattr(
            "app.workflows.code_review_flow.secondary_rerank",
            AsyncMock(return_value=[]),
        )

        from app.workflows.code_review_flow import run_code_review

        result = await run_code_review({"diff": "diff --git a/x b/x", "context": {}})
        assert result.get("reranked") is True

    async def test_no_reranked_key_when_disabled(self, monkeypatch):
        """When secondary rerank is disabled, result should not have reranked flag."""
        # Reset circuit breaker to avoid pollution from other tests
        import app.workflows.code_review_flow as crf
        crf._CODE_REVIEW_BREAKER.failure_count = 0
        crf._CODE_REVIEW_BREAKER.open_until = None

        monkeypatch.setattr(
            "app.workflows.code_review_flow.settings",
            type(
                "S",
                (),
                {
                    "secondary_rerank_enabled": False,
                    "secondary_rerank_targets": [],
                },
            )(),
        )

        from app.workflows.code_review_flow import run_code_review

        result = await run_code_review({"diff": "diff --git a/x b/x", "context": {}})
        assert result.get("reranked") is not True
