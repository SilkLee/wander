"""Base agent class for LangChain agents."""

from typing import Any, Dict, List, Optional
from abc import ABC, abstractmethod

from langchain_classic.agents import AgentExecutor, create_openai_functions_agent
from langchain_classic.tools import BaseTool
from langchain_openai import ChatOpenAI

from app.config import settings


class BaseAgent(ABC):
    """
    Base class for all LangChain agents.

    Provides common functionality for agent creation and execution.
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        temperature: float = 0.0,
        max_iterations: Optional[int] = None,
        timeout: Optional[int] = None,
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

        # Initialize LLM
        self.llm = ChatOpenAI(
            model=self.model_name,
            temperature=self.temperature,
            openai_api_key=settings.openai_api_key,
        )

    @abstractmethod
    def get_tools(self) -> List[BaseTool]:
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
    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
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
        Create AgentExecutor with configured tools and settings.

        Returns:
            Configured AgentExecutor
        """

        tools = self.get_tools()
        
        # Create prompt template
        from langchain_classic.prompts import ChatPromptTemplate, MessagesPlaceholder
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.get_system_prompt()),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])

        # Create agent
        agent = create_openai_functions_agent(
            llm=self.llm,
            tools=tools,
            prompt=prompt,
        )

        # Create executor
        executor = AgentExecutor(
            agent=agent,
            tools=tools,
            max_iterations=self.max_iterations,
            verbose=True,
            return_intermediate_steps=True,
        )

        return executor
