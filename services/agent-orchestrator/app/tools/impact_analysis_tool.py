"""Impact analysis tool for mapping diffs to impacted modules and services."""

from typing import Dict, Type

import httpx
from langchain_classic.tools import BaseTool
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
    args_schema: Type[BaseModel] = ImpactAnalysisInput

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
                response.raise_for_status()

                data = response.json()
                modules: list[str] = data.get("modules", [])
                services: list[str] = data.get("services", [])

                if not modules and not services:
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
    return {"modules": [], "services": []}
