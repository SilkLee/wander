"""LangChain tools agent for code-change analysis.

Combines RepoSearchTool, DependencyScanTool, and ImpactAnalysisTool
into a single ReAct agent that analyses diffs and returns structured
analysis + tool outputs.
"""

import asyncio
from typing import Any

from langchain.tools import BaseTool

from app.agents.base import BaseAgent
from app.models.agent_reports import ImpactReport, PRSummary
from app.tools.dependency_scan_tool import DependencyScanTool
from app.tools.impact_analysis_tool import ImpactAnalysisTool
from app.tools.repo_search_tool import RepoSearchTool
from app.workflows.stability import CircuitBreaker, run_with_retry


class LangChainToolsAgent(BaseAgent):
    """Agent that uses repo search, dependency scan, and impact analysis tools.

    Designed for PR / code-change analysis workflows.  The ``execute``
    method returns a dict with ``analysis`` (str) and ``outputs`` (dict)
    keys so callers have both a human-readable summary and structured
    tool results.
    """

    def get_tools(self) -> list[BaseTool]:
        """Return the three code-analysis tools."""
        return [
            RepoSearchTool(),
            DependencyScanTool(),
            ImpactAnalysisTool(),
        ]

    def get_system_prompt(self) -> str:
        """Return a prompt that guides the agent through code-change analysis."""
        return (
            "You are a senior software engineer specialising in code-change analysis.\n"
            "\n"
            "Given a diff (and optional context), you should:\n"
            "1. Search the repository for affected files and symbols.\n"
            "2. Scan the diff for dependency changes and assess risk.\n"
            "3. Perform impact analysis to identify affected modules and services.\n"
            "4. Synthesise a concise analysis summary with key findings.\n"
            "\n"
            "Use the available tools to gather evidence before summarising.\n"
            "Be concise but thorough."
        )

    async def execute(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """Run the tools agent and return analysis + outputs.

        Args:
            inputs: Must contain ``diff`` (str).  May contain ``context`` (dict).

        Returns:
            Dict with keys:
                - ``analysis``: str – human-readable summary from the agent.
                - ``outputs``: dict – contains ``raw_output`` (str) and
                  ``tool_outputs`` (list of dicts with ``tool`` and ``result``).

        Raises:
            RuntimeError: If agent execution fails.
        """
        diff_raw = inputs.get("diff", "")
        diff = diff_raw if isinstance(diff_raw, str) else ""
        context_raw = inputs.get("context", {})
        context = context_raw if isinstance(context_raw, dict) else {}

        agent_input = (
            f"Analyse the following diff and provide a summary:\n\n"
            f"DIFF:\n{diff[:5000]}\n\n"
            f"CONTEXT:\n{context}\n"
        )

        executor = self.create_executor()

        base_state: dict[str, Any] = {
            "errors": [],
            "retry_summary": {},
            "degraded": False,
        }

        if inputs.get("simulate_breaker"):
            for _ in range(_TOOLS_AGENT_BREAKER.threshold):
                _TOOLS_AGENT_BREAKER.record_failure()
        if _TOOLS_AGENT_BREAKER.is_open():
            base_state["retry_summary"]["langchain_tool_agent"] = 0
            base_state["errors"].append(
                {
                    "node": "langchain_tool_agent",
                    "error_type": "dependency",
                    "message": "circuit breaker open",
                    "retry_attempts": 0,
                    "degraded": True,
                }
            )
            base_state["degraded"] = True
            return {
                "analysis": "",
                "outputs": _empty_outputs(),
                "intermediate_summary": base_state,
            }

        async def invoke() -> dict[str, Any] | None:
            return await asyncio.to_thread(executor.invoke, {"input": agent_input})

        retries = 1
        timeout_seconds = float(self.timeout)
        result, error = await run_with_retry(
            invoke, retries=retries, timeout_seconds=timeout_seconds
        )
        if error is not None:
            _TOOLS_AGENT_BREAKER.record_failure()
            base_state["retry_summary"]["langchain_tool_agent"] = retries
            base_state["errors"].append(
                {
                    "node": "langchain_tool_agent",
                    "error_type": "unknown",
                    "message": str(error),
                    "retry_attempts": retries,
                    "degraded": True,
                }
            )
            base_state["degraded"] = True
            return {
                "analysis": "",
                "outputs": _empty_outputs(),
                "intermediate_summary": base_state,
            }

        _TOOLS_AGENT_BREAKER.record_success()
        base_state["retry_summary"]["langchain_tool_agent"] = 0

        output_text: str = ""
        intermediate_steps: list[tuple[Any, Any]] = []
        if result is not None:
            output_text = result.get("output", "")
            intermediate_steps = result.get("intermediate_steps", [])

        tool_outputs: list[dict[str, str]] = []
        impact_notes = ""
        for action, observation in intermediate_steps:
            tool_name = getattr(action, "tool", "unknown")
            observation_text = str(observation)
            tool_outputs.append(
                {
                    "tool": tool_name,
                    "result": observation_text,
                }
            )
            if tool_name == "impact_analysis" and not impact_notes:
                impact_notes = observation_text

        outputs = {
            "pr_summary": PRSummary(summary=output_text, key_risks=[], actions=[]),
            "risk_findings": [],
            "dependency_risks": [],
            "impact_report": ImpactReport(services=[], modules=[], notes=impact_notes),
            "tool_outputs": tool_outputs,
        }

        return {
            "analysis": output_text,
            "outputs": outputs,
            "intermediate_summary": base_state,
        }


async def run_tool_agent(inputs: dict[str, Any]) -> dict[str, Any]:
    """Convenience wrapper that creates a ``LangChainToolsAgent`` and executes it.

    Args:
        inputs: Forwarded to :meth:`LangChainToolsAgent.execute`.

    Returns:
        The dict returned by ``execute`` (``analysis`` + ``outputs``).
    """
    agent = LangChainToolsAgent()
    return await agent.execute(inputs)


_TOOLS_AGENT_BREAKER = CircuitBreaker(threshold=2, cooldown_seconds=30.0)


def _empty_outputs() -> dict[str, Any]:
    return {
        "pr_summary": PRSummary(summary="", key_risks=[], actions=[]),
        "risk_findings": [],
        "dependency_risks": [],
        "impact_report": ImpactReport(services=[], modules=[], notes=""),
        "tool_outputs": [],
    }
