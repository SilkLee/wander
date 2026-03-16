"""Dependency scan tool for detecting dependency and version changes in diffs."""

from typing import Any, Optional

import httpx
from langchain.tools import BaseTool
from langchain_core.tools import ArgsSchema
from pydantic import BaseModel, Field, field_validator

from app.config import settings


class DependencyScanInput(BaseModel):
    """Input schema for dependency scan (single-input for ZeroShotAgent)."""

    diff: str = Field(description="Git diff content to scan for dependency changes")

    @field_validator("diff")
    @classmethod
    def diff_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("diff must not be empty")
        return v


class DependencyScanTool(BaseTool):
    """
    Tool for scanning diffs for dependency and version changes.

    Connects to the Indexing Service to analyse dependency file
    modifications (requirements.txt, package.json, go.mod, etc.)
    and report risk levels for each change.
    """

    name: str = "dependency_scan"
    description: str = (
        "Scan a git diff for dependency and version changes. "
        "Use this tool when you need to detect added, removed, or "
        "upgraded dependencies and assess their risk level."
    )
    args_schema: Optional[ArgsSchema] = DependencyScanInput

    def _run(self, diff: str) -> str:
        """Synchronous scan (not used in async context)."""
        raise NotImplementedError("Use async version (arun)")

    async def _arun(self, diff: str) -> str:
        """
        Perform async dependency scan against the indexing service.

        Args:
            diff: Git diff content to scan.

        Returns:
            Formatted dependency change results.
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{settings.indexing_service_url}/dependency-scan",
                    json={"diff": diff},
                )
                _ = response.raise_for_status()

                data = response.json()
                raw_changes = data.get("changes") if isinstance(data, dict) else None
                changes: list[Any] = raw_changes if isinstance(raw_changes, list) else []

                if len(changes) == 0:
                    return "No dependency changes detected in the provided diff."

                formatted: list[str] = ["Dependency changes detected:\n"]
                for i, entry in enumerate(changes, 1):
                    change = entry if isinstance(entry, dict) else {}
                    package = change.get("package", "unknown")
                    old_ver = change.get("old_version", "N/A")
                    new_ver = change.get("new_version", "N/A")
                    risk = change.get("risk", "unknown")
                    formatted.append(f"{i}. {package}: {old_ver} → {new_ver} (risk: {risk})\n")

                return "\n".join(formatted)

        except httpx.HTTPStatusError as e:
            return f"Error scanning dependencies: {e}"

        except httpx.RequestError as e:
            return f"Dependency scan service unavailable: {e}"


def dependency_scan(filename: str) -> list[str]:
    """Simple synchronous wrapper kept for backward compatibility with plan tests."""
    from pathlib import Path

    matches: list[str] = []
    for path in Path(".").rglob("*"):
        if filename.lower() in path.name.lower():
            matches.append(str(path))
    return matches
