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


class BaseAgent(ABC):
    """
    Base class for all LangChain agents.

    Provides common functionality for agent creation and execution.
    """

    model_name: str
    temperature: float
    max_iterations: int
    timeout: int
    llm: BaseChatModel

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

        # Initialize LLM based on backend selection
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
    async def execute(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """
        Execute agent workflow.

        Args:
            inputs: Input parameters for the agent

        Returns:
            Agent execution results
        """
        pass

    def create_executor(self) -> object:
        """
        Create a compiled agent graph with configured tools and settings.

        Uses langchain create_agent which builds a tool-calling loop.

        Returns:
            Compiled agent graph
        """

        tools = self.get_tools()

        agent = create_agent(
            model=self.llm,
            tools=tools,
            system_prompt=self.get_system_prompt(),
        )

        return agent
