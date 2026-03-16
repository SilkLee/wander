from dataclasses import dataclass
import logging
from typing import Optional

from app.domain.models.log_analysis import LogAnalysis
from app.application.ports import AgentPort, LanggraphPort, ParserPort, RepositoryPort
from app.domain.models.confidence import Confidence
from app.domain.models.root_cause import RootCause
from app.domain.models.severity import Severity
from app.domain.events import AnalysisCompletedEvent
from app.infrastructure.events import EventBus

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AnalysisResult:
    analysis: LogAnalysis
    langgraph_result: Optional[dict[str, object]] = None


class AnalyzeLogUseCase:
    def __init__(
        self,
        agent: AgentPort,
        parser: ParserPort,
        repository: RepositoryPort,
        event_bus: EventBus,
        langgraph: Optional[LanggraphPort] = None,
    ) -> None:
        self.agent: AgentPort = agent
        self.parser: ParserPort = parser
        self.repository: RepositoryPort = repository
        self.event_bus: EventBus = event_bus
        self.langgraph: Optional[LanggraphPort] = langgraph

    async def execute(self, log_content: str) -> AnalysisResult:
        # 1. Validate input
        if not log_content or not log_content.strip():
            raise ValueError("Log content cannot be empty")

        # 2. Call agent
        raw_result: dict[str, object] = await self.agent.analyze_logs(log_content)

        # 3. Parse to domain components
        severity: Severity
        confidence: Confidence
        root_causes: list[RootCause]
        severity, confidence, root_causes = self.parser.parse_analysis_result(raw_result)

        # 4. Create domain model (enforces invariants via __post_init__)
        summary_value = raw_result.get("summary")
        summary = summary_value if isinstance(summary_value, str) else ""
        analysis = LogAnalysis(
            log_content=log_content,
            severity=severity,
            confidence=confidence,
            root_causes=root_causes,
            summary=summary,
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
        langgraph_result: Optional[dict[str, object]] = None
        if self.langgraph is not None:
            try:
                langgraph_result = await self.langgraph.run({"log_content": log_content})
            except Exception:
                logger.exception("LangGraph enrichment failed")

        return AnalysisResult(analysis=analysis, langgraph_result=langgraph_result)
