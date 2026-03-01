"""LangChain agent adapter implementing AgentPort."""

import asyncio

from app.agents.analyzer import LogAnalyzerAgent
from app.application.ports import AgentPort


class LangChainAgentAdapter(AgentPort):
    """Adapter wrapping LogAnalyzerAgent to implement AgentPort interface.
    
    This adapter bridges the application layer (AgentPort) with the infrastructure layer
    (LogAnalyzerAgent), allowing dependency injection and testing with mock implementations.
    
    The adapter is responsible for:
    1. Wrapping the existing LogAnalyzerAgent implementation
    2. Converting inputs to agent-compatible format
    3. Returning raw dict output (parsing is parser's responsibility)
    4. Handling async execution and error scenarios
    """

    def __init__(self) -> None:
        """Initialize adapter with LogAnalyzerAgent instance.
        
        Raises:
            Exception: If agent initialization fails
        """
        self._agent: LogAnalyzerAgent
        try:
            self._agent = LogAnalyzerAgent()
        except Exception as e:
            raise RuntimeError(f"Failed to initialize LogAnalyzerAgent: {e}")

    async def analyze_logs(self, log_content: str) -> dict[str, object]:
        """Analyze logs using LangChain agent and return raw dict.
        
        Wraps LogAnalyzerAgent.execute() to match AgentPort interface.
        Returns raw dict from agent (not domain models - that's parser's job).
        
        Args:
            log_content: Raw log text to analyze (will be truncated if too long)
            
        Returns:
            Dict containing raw agent analysis results:
            - 'analysis_id': Unique identifier (str)
            - 'root_cause': Extracted root cause description (str)
            - 'severity': Severity level (str: critical/high/medium/low)
            - 'suggested_fixes': List of fix suggestions (list[str])
            - 'references': Related documentation URLs (list[str])
            - 'confidence': Confidence score (float: 0.0-1.0)
            - 'raw_output': Full agent output for debugging (str)
            
        Raises:
            ValueError: If log_content is empty
            RuntimeError: If agent execution fails or times out
            Exception: For other unexpected errors
        """
        if not log_content or not log_content.strip():
            raise ValueError("log_content cannot be empty")

        try:
            # Run agent.execute() in thread pool (it's synchronous)
            result = await asyncio.to_thread(  # type: ignore
                self._agent.execute,
                {
                    "log_content": log_content,
                    "log_type": "build",
                    "context": {},
                },
            )


            # Validate result has required keys
            required_keys: set[str] = {
                "analysis_id",
                "root_cause",
                "severity",
                "suggested_fixes",
                "references",
                "confidence",
            }
            missing_keys = required_keys - set(result.keys())  # type: ignore
            if missing_keys:
                raise RuntimeError(
                    f"Agent returned incomplete result. Missing keys: {missing_keys}"
                )

            return result  # type: ignore

        except asyncio.TimeoutError as e:
            raise RuntimeError(f"Agent execution timed out: {e}")
        except ValueError as e:
            # Re-raise validation errors
            raise ValueError(f"Agent validation error: {e}")
        except Exception as e:
            raise RuntimeError(f"Agent execution failed: {type(e).__name__}: {e}")
