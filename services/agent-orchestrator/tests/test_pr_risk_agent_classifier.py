"""Tests for PR risk agent wired to model-service classifier.

Covers:
- run_pr_risk_agent calls classify_risk and returns risk_label
- Propagates different labels (high / low / medium)
- Handles classifier errors gracefully (fallback)
"""


from unittest.mock import AsyncMock, patch


# ---------------------------------------------------------------------------
# Happy-path: classifier label flows through
# ---------------------------------------------------------------------------


class TestPRRiskAgentUsesClassifier:
    """run_pr_risk_agent should delegate to classify_risk and surface risk_label."""

    async def test_returns_risk_label_from_classifier(self):
        """Core contract: risk_label in result matches classifier output."""
        from app.agents.pr_risk_agent import run_pr_risk_agent

        with patch(
            "app.agents.pr_risk_agent.classify_risk",
            new_callable=AsyncMock,
            return_value={"label": "high", "score": 0.9},
        ):
            result = await run_pr_risk_agent({"diff": "diff --git a/x b/x"})

        assert result["risk_label"] == "high"

    async def test_returns_low_label(self):
        from app.agents.pr_risk_agent import run_pr_risk_agent

        with patch(
            "app.agents.pr_risk_agent.classify_risk",
            new_callable=AsyncMock,
            return_value={"label": "low", "score": 0.1},
        ):
            result = await run_pr_risk_agent({"diff": "diff --git a/y b/y"})

        assert result["risk_label"] == "low"

    async def test_returns_medium_label(self):
        from app.agents.pr_risk_agent import run_pr_risk_agent

        with patch(
            "app.agents.pr_risk_agent.classify_risk",
            new_callable=AsyncMock,
            return_value={"label": "medium", "score": 0.5},
        ):
            result = await run_pr_risk_agent({"diff": "diff --git a/z b/z"})

        assert result["risk_label"] == "medium"

    async def test_passes_diff_to_classifier(self):
        """Verify the diff text is actually forwarded to classify_risk."""
        from app.agents.pr_risk_agent import run_pr_risk_agent

        mock_classify = AsyncMock(return_value={"label": "medium", "score": 0.5})
        with patch("app.agents.pr_risk_agent.classify_risk", mock_classify):
            await run_pr_risk_agent({"diff": "my-diff-content"})

        mock_classify.assert_awaited_once_with("my-diff-content")

    async def test_result_is_dict(self):
        from app.agents.pr_risk_agent import run_pr_risk_agent

        with patch(
            "app.agents.pr_risk_agent.classify_risk",
            new_callable=AsyncMock,
            return_value={"label": "low", "score": 0.2},
        ):
            result = await run_pr_risk_agent({"diff": "diff"})

        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# Error handling: classifier failure → fallback
# ---------------------------------------------------------------------------


class TestPRRiskAgentClassifierError:
    """When classify_risk raises, agent should return a degraded/fallback result."""

    async def test_classifier_error_returns_fallback_label(self):
        from app.agents.pr_risk_agent import run_pr_risk_agent

        with patch(
            "app.agents.pr_risk_agent.classify_risk",
            new_callable=AsyncMock,
            side_effect=RuntimeError("connection refused"),
        ):
            result = await run_pr_risk_agent({"diff": "diff"})

        # Fallback label when classifier is unavailable
        assert result["risk_label"] == "medium"

    async def test_classifier_error_sets_degraded_flag(self):
        from app.agents.pr_risk_agent import run_pr_risk_agent

        with patch(
            "app.agents.pr_risk_agent.classify_risk",
            new_callable=AsyncMock,
            side_effect=RuntimeError("timeout"),
        ):
            result = await run_pr_risk_agent({"diff": "diff"})

        assert result.get("degraded") is True

    async def test_classifier_error_includes_error_info(self):
        from app.agents.pr_risk_agent import run_pr_risk_agent

        with patch(
            "app.agents.pr_risk_agent.classify_risk",
            new_callable=AsyncMock,
            side_effect=RuntimeError("service down"),
        ):
            result = await run_pr_risk_agent({"diff": "diff"})

        assert "error" in result
        assert "service down" in result["error"]
