"""Base agent class for LangChain agents."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import SecretStr

from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.tools import BaseTool

from app.config import settings
from app.llm import ModelServiceLLM


class _AgentExecutorCompat:
    """
    Compatibility wrapper around LangChain 1.x create_agent graph.

    Translates the old AgentExecutor interface:
        executor.invoke({"input": str}) -> {"output": str, "intermediate_steps": []}
    to the new CompiledStateGraph interface:
        graph.invoke({"messages": [...]}) -> {"messages": [...]}
    """

    def __init__(self, graph: Any) -> None:
        self.graph = graph

    def invoke(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """Invoke agent with old-style {"input": str} interface."""
        user_input = inputs.get("input", "")
        result = self.graph.invoke(
            {"messages": [{"role": "user", "content": user_input}]}
        )
        # Extract the final assistant message as "output"
        messages = result.get("messages", [])
        output = ""
        for msg in reversed(messages):
            # Check for AIMessage or dict with role=assistant
            if hasattr(msg, "content") and hasattr(msg, "type") and msg.type == "ai":
                output = msg.content
                break
            elif isinstance(msg, dict) and msg.get("role") == "assistant":
                output = msg.get("content", "")
                break
        return {"output": output, "intermediate_steps": []}


class BaseAgent(ABC):
    """
    Base class for all LangChain agents.

    Provides common functionality for agent creation and execution.
    """

    model_name: str
    temperature: float
    max_iterations: int
    timeout: int
    llm: BaseChatModel | ModelServiceLLM

    def __init__(
        self,
        model_name: str | None = None,
        temperature: float = 0.0,
        max_iterations: int | None = None,
        timeout: int | None = None,
    ):
        """
        Initialize base agent.

        Args:
            model_name: OpenAI model name (default: from settings)
            temperature: Model temperature (0.0 = deterministic)
            max_iterations: Maximum agent iterations
            timeout: Execution timeout in seconds
        """
        self.model_name = model_name or settings.openai_model
        self.temperature = temperature
        self.max_iterations = max_iterations or settings.agent_max_iterations
        self.timeout = timeout or settings.agent_timeout_seconds

        if settings.use_local_model or not settings.openai_api_key:
            self.llm = ModelServiceLLM(
                model_service_url=settings.model_service_url,
                temperature=self.temperature,
                max_tokens=512,
                timeout=300,
            )
        else:
            self.llm = init_chat_model(
                model_provider="openai",
                model=self.model_name,
                temperature=self.temperature,
                api_key=SecretStr(settings.openai_api_key),
            )

    @abstractmethod
    def get_tools(self) -> list[BaseTool]:
        """
        Get list of tools for this agent.

        Returns:
            List of LangChain tools
        """
        pass

    @abstractmethod
    def get_system_prompt(self) -> str:
        """
        Get system prompt for this agent.

        Returns:
            System prompt string
        """
        pass

    @abstractmethod
    async def execute(self, inputs: dict[str, object]) -> dict[str, object]:
        """
        Execute agent workflow.

        Args:
            inputs: Input parameters for the agent

        Returns:
            Agent execution results
        """
        pass

    def create_executor(self) -> _AgentExecutorCompat:
        """
        Create a compiled agent graph with configured tools and settings.

        Uses LangChain 1.x create_agent which builds a tool-calling loop.
        Returns a compatibility wrapper matching the old AgentExecutor interface.

        Returns:
            Compatibility wrapper with .invoke({"input": str}) interface
        """
        tools = self.get_tools()
        system_prompt = self.get_system_prompt()

        graph = create_agent(
            model=self.llm,
            tools=tools,
            system_prompt=system_prompt,
        )

        return _AgentExecutorCompat(graph)
