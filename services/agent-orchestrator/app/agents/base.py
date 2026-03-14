"""Base agent class for LangChain agents."""

from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import SecretStr

from langchain.agents import AgentExecutor, create_react_agent
from langchain.chat_models import init_chat_model
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import PromptTemplate
from langchain_core.tools import BaseTool

from app.config import settings
from app.llm import ModelServiceLLM
from app.agents.output_parser import create_lenient_parsing_error_handler


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

    def create_executor(self) -> AgentExecutor:
        """
        Create a compiled agent graph with configured tools and settings.

        Uses langchain create_agent which builds a tool-calling loop.

        Returns:
            Compiled agent graph
        """

        tools = self.get_tools()

        prompt = PromptTemplate.from_template(
            self.get_system_prompt()
            + "\n\n"
            + "You have access to the following tools:\n\n"
            + "{tools}\n\n"
            + "Use the following format:\n\n"
            + "Question: the input question you must answer\n"
            + "Thought: you should always think about what to do\n"
            + "Action: the action to take, should be one of [{tool_names}]\n"
            + "Action Input: the input to the action\n"
            + "Observation: the result of the action\n"
            + "... (this Thought/Action/Action Input/Observation can repeat N times)\n"
            + "Thought: I now know the final answer\n"
            + "Final Answer: the final answer to the original input question\n\n"
            + "Begin!\n\n"
            + "Question: {input}\n"
            + "Thought:{agent_scratchpad}"
        )

        agent = create_react_agent(llm=self.llm, tools=tools, prompt=prompt)

        executor = AgentExecutor(
            agent=agent,
            tools=tools,
            max_iterations=self.max_iterations,
            verbose=True,
            return_intermediate_steps=True,
            handle_parsing_errors=create_lenient_parsing_error_handler(),
        )

        return executor
