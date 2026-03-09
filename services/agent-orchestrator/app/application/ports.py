"""Ports (interfaces) defining contracts for external dependencies.

Uses typing.Protocol for dependency inversion - allowing any implementation
that matches the interface, enabling easy testing with mocks.
"""

from collections.abc import Mapping
from typing import Optional, Protocol

from app.domain.models.log_analysis import LogAnalysis
from app.domain.models.confidence import Confidence
from app.domain.models.root_cause import RootCause
from app.domain.models.severity import Severity


class AgentPort(Protocol):
    """Port for LLM-based analysis agent.
    
    Any implementation that provides analyze_logs method matches this interface.
    Enables dependency injection and testing without concrete implementations.
    """

    async def analyze_logs(self, log_content: str) -> dict[str, object]:
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

    def parse_analysis_result(
        self, raw_result: Mapping[str, object]
    ) -> tuple[Severity, Confidence, list[RootCause]]:
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


class LanggraphPort(Protocol):
    """Port for LangGraph-based multi-agent analysis workflow.

    Wraps the LangGraph triage graph that parses logs, diagnoses root causes,
    gathers evidence, and produces remediation steps.
    """

    async def run(self, inputs: Mapping[str, object]) -> dict[str, object]:
        """Execute the LangGraph workflow on the given inputs.

        Args:
            inputs: Dict containing at minimum 'log_content' (str)

        Returns:
            Dict with keys: 'raw_log', 'parsed' (ParsedLog), 'diagnosis' (Diagnosis),
            'evidence' (EvidenceBundle), 'remediation' (Remediation)
        """
        ...
