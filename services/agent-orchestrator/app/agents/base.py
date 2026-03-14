"""Base agent class for LangChain agents."""

from typing import Any, Dict, List, Optional
from abc import ABC, abstractmethod

from langchain.agents import create_react_agent, AgentExecutor
from langchain_core.tools import BaseTool
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.language_models.llms import LLM

from app.config import settings
from app.llm import ModelServiceLLM
from app.agents.output_parser import create_lenient_parsing_error_handler


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
                timeout=300,  # Increased for CPU inference (Qwen2.5-1.5B: ~30-60s per call)
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

        prompt = PromptTemplate.from_template(
            self.get_system_prompt() + "\n\n"
            "You have access to the following tools:\n\n"
            "{tools}\n\n"
            "Use the following format:\n\n"
            "Question: the input question you must answer\n"
            "Thought: you should always think about what to do\n"
            "Action: the action to take, should be one of [{tool_names}]\n"
            "Action Input: the input to the action\n"
            "Observation: the result of the action\n"
            "... (this Thought/Action/Action Input/Observation can repeat N times)\n"
            "Thought: I now know the final answer\n"
            "Final Answer: the final answer to the original input question\n\n"
            "Begin!\n\n"
            "Question: {input}\n"
            "Thought:{agent_scratchpad}"
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
