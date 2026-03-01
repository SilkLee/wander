"""Use case for analyzing logs and producing actionable insights.

AnalyzeLogUseCase orchestrates the workflow:
1. Call agent to analyze logs
2. Parse results into domain models
3. Apply business rules
4. Persist analysis results
5. Return domain model to caller
"""

from typing import TYPE_CHECKING

from app.domain.models.log_analysis import LogAnalysis
from app.application.ports import AgentPort, ParserPort, RepositoryPort
from app.domain.events import AnalysisCompletedEvent
from app.infrastructure.events import EventBus

if TYPE_CHECKING:
    from typing import Protocol


class AnalyzeLogUseCase:
    """Use case for analyzing logs and identifying issues.
    
    Orchestrates external agents, parsers, and repositories to provide
    a complete log analysis workflow respecting domain invariants.
    
    Dependencies are injected via constructor using Protocol interfaces
    for dependency inversion - enabling testing with any compatible mock.
    
    Attributes:
        agent: Port implementation for LLM-based analysis
        parser: Port implementation for parsing raw results
        repository: Port implementation for persistence
    """

    def __init__(
        self,
        agent: AgentPort,
        parser: ParserPort,
        repository: RepositoryPort,
        event_bus: EventBus,
    ) -> None:
        """Initialize use case with required port dependencies.
        
        Args:
            agent: Implementation of AgentPort for log analysis
            parser: Implementation of ParserPort for result parsing
            repository: Implementation of RepositoryPort for persistence
            event_bus: Implementation of EventBus for event publishing
            
        Raises:
            TypeError: If any dependency doesn't match expected Protocol
        """
        self.agent = agent
        self.parser = parser
        self.repository = repository
        self.event_bus = event_bus

    async def execute(self, log_content: str) -> LogAnalysis:
        """Execute the log analysis workflow.
        
        This method implements the complete use case flow:
        1. Validate input (non-empty log content)
        2. Call agent to analyze logs
        3. Parse raw agent output into domain components
        4. Create LogAnalysis domain model
        5. Apply business rules (via domain invariants)
        6. Persist to repository
        7. Return domain model
        
        Args:
            log_content: Raw log text to analyze
            
        Returns:
            LogAnalysis domain model with results
            
        Raises:
            ValueError: If log_content is empty/invalid
            Exception: If agent call, parsing, or persistence fails
            
        Example:
            >>> use_case = AnalyzeLogUseCase(agent, parser, repo)
            >>> analysis = await use_case.execute("ERROR in component X...")
            >>> print(analysis.severity)
            <Severity.HIGH: 3>
        """
        # 1. Validate input
        if not log_content or not log_content.strip():
            raise ValueError("Log content cannot be empty")

        # 2. Call agent
        raw_result = await self.agent.analyze_logs(log_content)

        # 3. Parse to domain components
        severity, confidence, root_causes = self.parser.parse_analysis_result(raw_result)

        # 4. Create domain model (enforces invariants via __post_init__)
        analysis = LogAnalysis(
            log_content=log_content,
            severity=severity,
            confidence=confidence,
            root_causes=root_causes,
            summary=raw_result.get("summary", ""),
        )

        # 5. Business rules already enforced in domain model constructor

        # 6. Create and register domain event
        event = AnalysisCompletedEvent(
            aggregate_id=analysis.id,
            severity=analysis.severity,
            is_critical=analysis.is_critical(),
            confidence_score=analysis.confidence.score,
            root_cause_count=len(analysis.root_causes),
        )
        analysis.add_domain_event(event)

        # 7. Persist to repository
        await self.repository.save(analysis)

        # 8. Collect and publish domain events
        events = analysis.clear_domain_events()
        for evt in events:
            await self.event_bus.publish(evt)

        # 9. Return domain model
        return analysis
