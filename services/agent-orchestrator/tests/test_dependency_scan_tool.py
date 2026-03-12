"""Tests for the dependency_scan_tool module."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.tools.dependency_scan_tool import (
    DependencyScanInput,
    DependencyScanTool,
    dependency_scan,
)


class TestDependencyScanInput:
    """Validate the Pydantic input schema."""

    def test_valid_diff(self):
        inp = DependencyScanInput(diff="diff --git a/requirements.txt b/requirements.txt")
        assert inp.diff == "diff --git a/requirements.txt b/requirements.txt"

    def test_empty_diff_rejected(self):
        with pytest.raises(Exception):
            DependencyScanInput(diff="")


class TestDependencyScanToolMetadata:
    """Tool metadata exposed to the LangChain agent."""

    def test_name(self):
        tool = DependencyScanTool()
        assert tool.name == "dependency_scan"

    def test_description_mentions_dependency(self):
        tool = DependencyScanTool()
        assert "dependenc" in tool.description.lower()

    def test_args_schema(self):
        tool = DependencyScanTool()
        assert tool.args_schema is DependencyScanInput

    def test_sync_run_raises(self):
        tool = DependencyScanTool()
        with pytest.raises(NotImplementedError):
            tool._run(diff="test")


def test_dependency_scan_returns_list():
    result = dependency_scan("requirements.txt")
    assert isinstance(result, list)


class TestDependencyScanToolAsync:
    """Integration-style tests with mocked HTTP layer."""

    @pytest.fixture()
    def tool(self):
        return DependencyScanTool()

    @pytest.mark.asyncio
    async def test_returns_formatted_results(self, tool):
        mock_response = httpx.Response(
            200,
            json={
                "changes": [
                    {
                        "package": "requests",
                        "old_version": "2.28.0",
                        "new_version": "2.31.0",
                        "risk": "low",
                    }
                ]
            },
            request=httpx.Request("POST", "http://test/dependency-scan"),
        )
        with patch("app.tools.dependency_scan_tool.httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.post.return_value = mock_response
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            result = await tool._arun(diff="diff --git a/requirements.txt")

        assert "requests" in result
        assert "2.31.0" in result

    @pytest.mark.asyncio
    async def test_no_changes_returns_message(self, tool):
        mock_response = httpx.Response(
            200,
            json={"changes": []},
            request=httpx.Request("POST", "http://test/dependency-scan"),
        )
        with patch("app.tools.dependency_scan_tool.httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.post.return_value = mock_response
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            result = await tool._arun(diff="diff --git a/setup.py")

        assert "no" in result.lower()

    @pytest.mark.asyncio
    async def test_http_error_returns_error_message(self, tool):
        mock_request = httpx.Request("POST", "http://test/dependency-scan")
        mock_response = httpx.Response(500, request=mock_request)
        with patch("app.tools.dependency_scan_tool.httpx.AsyncClient") as MockClient:
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
        with patch("app.tools.dependency_scan_tool.httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.post.side_effect = httpx.RequestError("Connection refused")
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            result = await tool._arun(diff="something")

        assert "error" in result.lower() or "unavailable" in result.lower()

    @pytest.mark.asyncio
    async def test_multiple_changes_formatted(self, tool):
        mock_response = httpx.Response(
            200,
            json={
                "changes": [
                    {
                        "package": "flask",
                        "old_version": "2.3.0",
                        "new_version": "3.0.0",
                        "risk": "high",
                    },
                    {
                        "package": "pytest",
                        "old_version": "7.4.0",
                        "new_version": "8.0.0",
                        "risk": "medium",
                    },
                ]
            },
            request=httpx.Request("POST", "http://test/dependency-scan"),
        )
        with patch("app.tools.dependency_scan_tool.httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.post.return_value = mock_response
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            result = await tool._arun(diff="diff --git a/requirements.txt")

        assert "flask" in result
        assert "pytest" in result
        assert "high" in result.lower()
        assert "medium" in result.lower()
