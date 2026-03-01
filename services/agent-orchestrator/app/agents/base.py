"""Base agent class for LangChain agents."""

from typing import Any, Dict, List, Optional
from abc import ABC, abstractmethod

from langchain.agents import AgentExecutor
from langchain.tools import BaseTool
from langchain_openai import ChatOpenAI
from langchain_core.language_models.llms import LLM

from app.config import settings
from app.llm import ModelServiceLLM


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

        # Initialize LLM based on backend selection
        if settings.use_local_model:
            # Use local Model Service
            self.llm = ModelServiceLLM(
                model_service_url=settings.model_service_url,
                temperature=self.temperature,
                max_tokens=512,
                timeout=60,
            )
        else:
            # Use OpenAI
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
        
        Uses ReAct agent framework which works with any LLM (including GPT-2).
        ReAct agents use text-based reasoning instead of function calling.
        
        Returns:
            Configured AgentExecutor
        """

        tools = self.get_tools()
        
        # Create ReAct agent using initialize_agent (LangChain 1.x standard)
        # AgentType.ZERO_SHOT_REACT_DESCRIPTION works with any LLM (text-based reasoning)
        from langchain.agents import initialize_agent, AgentType
        
        executor = initialize_agent(
            tools=tools,
            llm=self.llm,
            agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
            max_iterations=self.max_iterations,
            verbose=True,
            return_intermediate_steps=True,
            handle_parsing_errors=True,  # Important: handle ReAct parsing errors gracefully
            agent_kwargs={
                "prefix": self.get_system_prompt(),
            }
        )
        
        return executor
