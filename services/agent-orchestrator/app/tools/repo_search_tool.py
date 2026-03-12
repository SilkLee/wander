"""Repo search tool for finding files and symbols in the codebase."""

from typing import Any

import httpx
from langchain.tools import BaseTool
from langchain_core.tools import ArgsSchema
from pydantic import BaseModel, Field, field_validator

from app.config import settings


class RepoSearchInput(BaseModel):
    """Input schema for repo search (single-input for ZeroShotAgent)."""

    query: str = Field(description="Search query for finding files and symbols in the repository")

    @field_validator("query")
    @classmethod
    def query_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("query must not be empty")
        return v


class RepoSearchTool(BaseTool):
    """
    Tool for searching repository files and symbols.

    Connects to the Indexing Service to perform search
    over indexed file paths and code symbols.
    """

    name: str = "repo_search"
    description: str = (
        "Search the repository for file paths and symbol definitions. "
        "Use this tool when you need to find files or symbols relevant to "
        "a code change or investigation."
    )
    args_schema: ArgsSchema | None = RepoSearchInput

    def _run(self, query: str) -> str:
        """Synchronous search (not used in async context)."""
        raise NotImplementedError("Use async version (arun)")

    async def _arun(self, query: str) -> str:
        """
        Perform async search against the indexing service.

        Args:
            query: Search query for files and symbols.

        Returns:
            Formatted search results.
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{settings.indexing_service_url}/search",
                    json={"query": query},
                )
                _ = response.raise_for_status()

                data = response.json()
                raw_results = data.get("results") if isinstance(data, dict) else None
                results: list[Any] = raw_results if isinstance(raw_results, list) else []

                if len(results) == 0:
                    return f"No results found for: {query}"

                formatted: list[str] = [f"Search results for '{query}':\n"]
                for i, entry in enumerate(results, 1):
                    result = entry if isinstance(entry, dict) else {}
                    file_path = result.get("file_path", "unknown")
                    symbol = result.get("symbol", "")
                    content = result.get("content", "")
                    score = result.get("score", 0.0)
                    formatted.append(
                        f"{i}. {file_path} — {symbol} (score: {score})\n   {content}\n"
                    )

                return "\n".join(formatted)

        except httpx.HTTPStatusError as e:
            return f"Error searching repository: {e}"

        except httpx.RequestError as e:
            return f"Repository search unavailable: {e}"


def repo_search(query: str) -> list[str]:
    """Simple synchronous wrapper kept for backward compatibility with plan tests."""
    from pathlib import Path

    matches: list[str] = []
    for path in Path(".").rglob("*"):
        if query.lower() in path.name.lower():
            matches.append(str(path))
    return matches
