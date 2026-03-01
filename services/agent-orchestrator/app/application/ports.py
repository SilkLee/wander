"""Ports (interfaces) defining contracts for external dependencies.

Uses typing.Protocol for dependency inversion - allowing any implementation
that matches the interface, enabling easy testing with mocks.
"""

from typing import Optional, Protocol

from app.domain.models.log_analysis import LogAnalysis


class AgentPort(Protocol):
    """Port for LLM-based analysis agent.
    
    Any implementation that provides analyze_logs method matches this interface.
    Enables dependency injection and testing without concrete implementations.
    """

    async def analyze_logs(self, log_content: str) -> dict:
        """Analyze logs using an LLM agent.
        
        Args:
            log_content: Raw log text to analyze
            
        Returns:
            Dict containing analysis results with keys:
            - 'severity': Severity level (str)
            - 'confidence': Confidence score (float)
            - 'root_causes': List of root cause dicts with 'description', 'component', 'remediation'
            - 'summary': Human-readable summary (str)
        """
        ...


class ParserPort(Protocol):
    """Port for parsing agent output into domain models.
    
    Handles conversion of agent results to domain-validated structures,
    enforcing business rules and invariants.
    """

    def parse_analysis_result(self, raw_result: dict) -> tuple:
        """Parse agent output into domain components.
        
        Args:
            raw_result: Raw dict from agent analysis
            
        Returns:
            Tuple of (severity: Severity, confidence: Confidence, root_causes: list[RootCause])
            
        Raises:
            ValueError: If parsing fails or validation violations occur
        """
        ...


class RepositoryPort(Protocol):
    """Port for persisting and retrieving log analyses.
    
    Abstracts storage concerns - implementations can use databases,
    caches, or any other persistence mechanism.
    """

    async def save(self, analysis: LogAnalysis) -> None:
        """Persist a log analysis to storage.
        
        Args:
            analysis: LogAnalysis domain model to save
            
        Raises:
            Exception: If persistence fails
        """
        ...

    async def get_by_id(self, analysis_id: str) -> Optional[LogAnalysis]:
        """Retrieve a log analysis by ID.
        
        Args:
            analysis_id: Unique identifier of analysis
            
        Returns:
            LogAnalysis if found, None otherwise
        """
        ...
