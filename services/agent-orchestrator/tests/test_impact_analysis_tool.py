"""Tests for the impact_analysis_tool module."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.tools.impact_analysis_tool import (
    ImpactAnalysisInput,
    ImpactAnalysisTool,
    impact_analysis,
)


class TestImpactAnalysisInput:
    """Validate the Pydantic input schema."""

    def test_valid_diff(self):
        inp = ImpactAnalysisInput(diff="diff --git a/x b/x")
        assert inp.diff == "diff --git a/x b/x"

    def test_empty_diff_rejected(self):
        with pytest.raises(Exception):
            ImpactAnalysisInput(diff="")


class TestImpactAnalysisToolMetadata:
    """Tool metadata exposed to the LangChain agent."""

    def test_name(self):
        tool = ImpactAnalysisTool()
        assert tool.name == "impact_analysis"

    def test_description_mentions_impact(self):
        tool = ImpactAnalysisTool()
        assert "impact" in tool.description.lower()

    def test_args_schema(self):
        tool = ImpactAnalysisTool()
        assert tool.args_schema is ImpactAnalysisInput

    def test_sync_run_raises(self):
        tool = ImpactAnalysisTool()
        with pytest.raises(NotImplementedError):
            tool._run(diff="test")


def test_impact_analysis_returns_dict():
    result = impact_analysis("diff --git a/x b/x")
    assert isinstance(result, dict)


class TestImpactAnalysisToolAsync:
    """Integration-style tests with mocked HTTP layer."""

    @pytest.fixture()
    def tool(self):
        return ImpactAnalysisTool()

    @pytest.mark.asyncio
    async def test_returns_formatted_results(self, tool):
        mock_response = httpx.Response(
            200,
            json={
                "modules": ["auth", "middleware"],
                "services": ["api-gateway"],
            },
            request=httpx.Request("POST", "http://test/impact-analysis"),
        )
        with patch("app.tools.impact_analysis_tool.httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.post.return_value = mock_response
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            result = await tool._arun(diff="diff --git a/auth.py")

        assert "auth" in result
        assert "api-gateway" in result

    @pytest.mark.asyncio
    async def test_empty_impact_returns_message(self, tool):
        mock_response = httpx.Response(
            200,
            json={"modules": [], "services": []},
            request=httpx.Request("POST", "http://test/impact-analysis"),
        )
        with patch("app.tools.impact_analysis_tool.httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.post.return_value = mock_response
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            result = await tool._arun(diff="diff --git a/setup.py")

        assert "no" in result.lower()

    @pytest.mark.asyncio
    async def test_http_error_returns_error_message(self, tool):
        mock_request = httpx.Request("POST", "http://test/impact-analysis")
        mock_response = httpx.Response(500, request=mock_request)
        with patch("app.tools.impact_analysis_tool.httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.post.side_effect = httpx.HTTPStatusError(
                "Server Error", request=mock_request, response=mock_response
            )
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            result = await tool._arun(diff="something")

        assert "error" in result.lower()

    @pytest.mark.asyncio
    async def test_network_error_returns_error_message(self, tool):
        with patch("app.tools.impact_analysis_tool.httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.post.side_effect = httpx.RequestError("Connection refused")
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            result = await tool._arun(diff="something")

        assert "error" in result.lower() or "unavailable" in result.lower()

    @pytest.mark.asyncio
    async def test_multiple_modules_formatted(self, tool):
        mock_response = httpx.Response(
            200,
            json={
                "modules": ["auth", "db", "cache"],
                "services": ["api-gateway", "ingestion"],
            },
            request=httpx.Request("POST", "http://test/impact-analysis"),
        )
        with patch("app.tools.impact_analysis_tool.httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.post.return_value = mock_response
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            result = await tool._arun(diff="diff --git a/requirements.txt")

        assert "auth" in result
        assert "db" in result
        assert "cache" in result
        assert "api-gateway" in result
        assert "ingestion" in result
