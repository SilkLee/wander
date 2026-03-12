"""Tests for the repo_search_tool module."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.tools.repo_search_tool import RepoSearchInput, RepoSearchTool, repo_search


class TestRepoSearchInput:
    """Validate the Pydantic input schema."""

    def test_valid_query(self):
        inp = RepoSearchInput(query="find auth handler")
        assert inp.query == "find auth handler"

    def test_empty_query_rejected(self):
        with pytest.raises(Exception):
            RepoSearchInput(query="")


def test_repo_search_returns_list():
    result = repo_search("README")
    assert isinstance(result, list)


class TestRepoSearchToolMetadata:
    """Tool metadata exposed to the LangChain agent."""

    def test_name(self):
        tool = RepoSearchTool()
        assert tool.name == "repo_search"

    def test_description_mentions_files_and_symbols(self):
        tool = RepoSearchTool()
        assert "file" in tool.description.lower()
        assert "symbol" in tool.description.lower()

    def test_args_schema(self):
        tool = RepoSearchTool()
        assert tool.args_schema is RepoSearchInput

    def test_sync_run_raises(self):
        tool = RepoSearchTool()
        with pytest.raises(NotImplementedError):
            tool._run(query="test")


class TestRepoSearchToolAsync:
    """Integration-style tests with mocked HTTP layer."""

    @pytest.fixture()
    def tool(self):
        return RepoSearchTool()

    @pytest.mark.asyncio
    async def test_returns_formatted_results(self, tool):
        mock_response = httpx.Response(
            200,
            json={
                "results": [
                    {
                        "file_path": "services/api/handler.py",
                        "symbol": "handle_request",
                        "content": "def handle_request(req):",
                        "score": 0.92,
                    }
                ]
            },
            request=httpx.Request("POST", "http://test/search"),
        )
        with patch("app.tools.repo_search_tool.httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.post.return_value = mock_response
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            result = await tool._arun(query="handle_request")

        assert "handler.py" in result
        assert "handle_request" in result
        assert "0.92" in result

    @pytest.mark.asyncio
    async def test_no_results_returns_message(self, tool):
        mock_response = httpx.Response(
            200,
            json={"results": []},
            request=httpx.Request("POST", "http://test/search"),
        )
        with patch("app.tools.repo_search_tool.httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.post.return_value = mock_response
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            result = await tool._arun(query="nonexistent_function")

        assert "no" in result.lower()

    @pytest.mark.asyncio
    async def test_http_error_returns_error_message(self, tool):
        mock_request = httpx.Request("POST", "http://test/search")
        mock_response = httpx.Response(500, request=mock_request)
        with patch("app.tools.repo_search_tool.httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.post.side_effect = httpx.HTTPStatusError(
                "Server Error", request=mock_request, response=mock_response
            )
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            result = await tool._arun(query="something")

        assert "error" in result.lower()

    @pytest.mark.asyncio
    async def test_network_error_returns_error_message(self, tool):
        with patch("app.tools.repo_search_tool.httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.post.side_effect = httpx.RequestError("Connection refused")
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            result = await tool._arun(query="something")

        assert "error" in result.lower() or "unavailable" in result.lower()

    @pytest.mark.asyncio
    async def test_multiple_results_formatted(self, tool):
        mock_response = httpx.Response(
            200,
            json={
                "results": [
                    {
                        "file_path": "app/auth.py",
                        "symbol": "authenticate",
                        "content": "def authenticate(token):",
                        "score": 0.95,
                    },
                    {
                        "file_path": "app/middleware.py",
                        "symbol": "AuthMiddleware",
                        "content": "class AuthMiddleware:",
                        "score": 0.88,
                    },
                ]
            },
            request=httpx.Request("POST", "http://test/search"),
        )
        with patch("app.tools.repo_search_tool.httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.post.return_value = mock_response
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            result = await tool._arun(query="auth")

        assert "auth.py" in result
        assert "middleware.py" in result
        assert "authenticate" in result
        assert "AuthMiddleware" in result
