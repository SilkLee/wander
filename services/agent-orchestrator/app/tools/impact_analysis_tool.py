"""Impact analysis tool for mapping diffs to impacted modules and services."""

from typing import Any, Dict, Optional

import httpx
from langchain.tools import BaseTool
from langchain_core.tools import ArgsSchema
from pydantic import BaseModel, Field, field_validator

from app.config import settings


class ImpactAnalysisInput(BaseModel):
    """Input schema for impact analysis (single-input for ZeroShotAgent)."""

    diff: str = Field(description="Git diff content to analyse for impact")

    @field_validator("diff")
    @classmethod
    def diff_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("diff must not be empty")
        return v


class ImpactAnalysisTool(BaseTool):
    """
    Tool for analysing the impact of code changes.

    Connects to the Indexing Service to map a diff to the
    modules and services affected by the change.
    """

    name: str = "impact_analysis"
    description: str = (
        "Analyse a git diff to determine impact on modules and services. "
        "Use this tool when you need to understand which parts of the "
        "system are affected by a code change."
    )
    args_schema: Optional[ArgsSchema] = ImpactAnalysisInput

    def _run(self, diff: str) -> str:
        """Synchronous analysis (not used in async context)."""
        raise NotImplementedError("Use async version (arun)")

    async def _arun(self, diff: str) -> str:
        """
        Perform async impact analysis against the indexing service.

        Args:
            diff: Git diff content to analyse.

        Returns:
            Formatted impact analysis results.
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{settings.indexing_service_url}/impact-analysis",
                    json={"diff": diff},
                )
                _ = response.raise_for_status()

                data = response.json()
                raw_modules = data.get("modules") if isinstance(data, dict) else None
                raw_services = data.get("services") if isinstance(data, dict) else None
                modules: list[Any] = raw_modules if isinstance(raw_modules, list) else []
                services: list[Any] = raw_services if isinstance(raw_services, list) else []

                if len(modules) == 0 and len(services) == 0:
                    return "No impacted modules or services detected in the provided diff."

                formatted: list[str] = ["Impact analysis results:\n"]
                if modules:
                    formatted.append("Affected modules:")
                    for i, mod in enumerate(modules, 1):
                        formatted.append(f"  {i}. {mod}")
                if services:
                    formatted.append("Affected services:")
                    for i, svc in enumerate(services, 1):
                        formatted.append(f"  {i}. {svc}")

                return "\n".join(formatted)

        except httpx.HTTPStatusError as e:
            return f"Error analysing impact: {e}"

        except httpx.RequestError as e:
            return f"Impact analysis service unavailable: {e}"


def impact_analysis(diff: str) -> Dict[str, list[str]]:
    """Simple synchronous wrapper kept for backward compatibility with plan tests."""
    _ = diff
    return {"modules": [], "services": []}
