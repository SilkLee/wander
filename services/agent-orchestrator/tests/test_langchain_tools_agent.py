"""Tests for the langchain_tools_agent module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.langchain_tools_agent import LangChainToolsAgent, run_tool_agent


class TestLangChainToolsAgentInit:
    """Verify agent initialises with expected tools and prompt."""

    def test_get_tools_returns_three_tools(self):
        with patch("app.agents.base.ModelServiceLLM"):
            agent = LangChainToolsAgent()
        tools = agent.get_tools()
        names = {t.name for t in tools}
        assert names == {"repo_search", "dependency_scan", "impact_analysis"}

    def test_get_system_prompt_mentions_analysis(self):
        with patch("app.agents.base.ModelServiceLLM"):
            agent = LangChainToolsAgent()
        prompt = agent.get_system_prompt()
        assert "analys" in prompt.lower()

    def test_tools_count_is_three(self):
        with patch("app.agents.base.ModelServiceLLM"):
            agent = LangChainToolsAgent()
        assert len(agent.get_tools()) == 3


class TestLangChainToolsAgentExecute:
    """Verify execute returns structured analysis dict."""

    @pytest.mark.asyncio
    async def test_execute_returns_analysis_and_outputs(self):
        with patch("app.agents.base.ModelServiceLLM"):
            agent = LangChainToolsAgent()

        mock_executor = MagicMock()
        mock_executor.invoke.return_value = {
            "output": "Root cause: missing dependency\nSeverity: high\nFix: add package",
            "intermediate_steps": [],
        }
        with patch.object(agent, "create_executor", return_value=mock_executor):
            result = await agent.execute({"diff": "diff --git a/x b/x", "context": {}})

        assert "analysis" in result
        assert "outputs" in result
        assert isinstance(result["analysis"], str)
        assert isinstance(result["outputs"], dict)
        assert "intermediate_summary" in result

    @pytest.mark.asyncio
    async def test_execute_outputs_contain_tool_results(self):
        with patch("app.agents.base.ModelServiceLLM"):
            agent = LangChainToolsAgent()

        mock_action = MagicMock()
        mock_action.tool = "repo_search"
        intermediate_steps = [(mock_action, "found: auth.py")]

        mock_executor = MagicMock()
        mock_executor.invoke.return_value = {
            "output": "Analysis complete",
            "intermediate_steps": intermediate_steps,
        }
        with patch.object(agent, "create_executor", return_value=mock_executor):
            result = await agent.execute({"diff": "diff --git a/x b/x", "context": {}})

        assert "tool_outputs" in result["outputs"]
        assert len(result["outputs"]["tool_outputs"]) == 1
        assert result["outputs"]["tool_outputs"][0]["tool"] == "repo_search"

    @pytest.mark.asyncio
    async def test_execute_handles_timeout(self):
        with patch("app.agents.base.ModelServiceLLM"):
            agent = LangChainToolsAgent(timeout=1)

        mock_executor = MagicMock()
        mock_executor.invoke.side_effect = Exception("timed out")
        with patch.object(agent, "create_executor", return_value=mock_executor):
            result = await agent.execute({"diff": "diff --git a/x b/x"})
        assert result["intermediate_summary"]["degraded"] is True


class TestRunToolAgent:
    """Verify the run_tool_agent convenience function."""

    @pytest.mark.asyncio
    async def test_returns_analysis_and_outputs(self):
        mock_result = {
            "analysis": "Root cause found",
            "outputs": {"raw_output": "text", "tool_outputs": []},
        }
        with patch("app.agents.langchain_tools_agent.LangChainToolsAgent") as MockAgent:
            instance = AsyncMock()
            instance.execute.return_value = mock_result
            MockAgent.return_value = instance

            result = await run_tool_agent({"diff": "diff --git a/x b/x", "context": {}})

        assert result["analysis"] == "Root cause found"
        assert "outputs" in result

    @pytest.mark.asyncio
    async def test_accepts_diff_input(self):
        with patch("app.agents.langchain_tools_agent.LangChainToolsAgent") as MockAgent:
            instance = AsyncMock()
            instance.execute.return_value = {
                "analysis": "ok",
                "outputs": {"raw_output": "", "tool_outputs": []},
            }
            MockAgent.return_value = instance

            result = await run_tool_agent({"diff": "some diff"})

        instance.execute.assert_called_once_with({"diff": "some diff"})
        assert result["analysis"] == "ok"

    @pytest.mark.asyncio
    async def test_propagates_error_on_failure(self):
        with patch("app.agents.langchain_tools_agent.LangChainToolsAgent") as MockAgent:
            instance = AsyncMock()
            instance.execute.side_effect = RuntimeError("Agent execution failed")
            MockAgent.return_value = instance

            with pytest.raises(RuntimeError, match="failed"):
                await run_tool_agent({"diff": "bad diff"})
