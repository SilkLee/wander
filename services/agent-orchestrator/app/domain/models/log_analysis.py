"""Log analysis aggregate root for domain model.

LogAnalysis is the aggregate root that orchestrates log analysis operations
and enforces business rules for determining actionability and criticality.
"""

from dataclasses import dataclass, field
from typing import Optional
from uuid import UUID, uuid4

from .confidence import Confidence
from .root_cause import RootCause
from .severity import Severity
from ..events import DomainEvent, AnalysisCompletedEvent


@dataclass(frozen=True)
class LogAnalysis:
    """Aggregate root for log analysis domain entity.
    
    LogAnalysis represents a complete analysis of logs, containing identified
    issues, their severity, confidence levels, and potential root causes.
    Enforces business rules about actionability and criticality.
    
    Attributes:
        id: Unique identifier for this analysis
        log_content: The raw log content that was analyzed
        severity: Severity level of identified issues
        confidence: Confidence level of the analysis
        root_causes: List of identified root causes
        summary: Human-readable summary of findings
        is_resolved: Whether the identified issues have been resolved
        
    Business Rules:
        - An analysis is actionable if confidence > 0.7 AND has at least one fix
        - An analysis is critical if severity is HIGH or CRITICAL
    """

    log_content: str
    severity: Severity
    confidence: Confidence
    root_causes: list[RootCause] = field(default_factory=list)
    summary: str = ""
    is_resolved: bool = False
    id: UUID = field(default_factory=uuid4)
    domain_events: list[DomainEvent] = field(default_factory=list, init=False, repr=False)

    def __post_init__(self) -> None:
        """Validate log analysis invariants.
        
        Raises:
            ValueError: If log_content is empty
        """
        if not self.log_content or not self.log_content.strip():
            raise ValueError("Log content cannot be empty")

    def is_actionable(self) -> bool:
        """Determine if analysis results warrant action.
        
        Business rule: An analysis is actionable if:
        - Confidence score is greater than 0.7 AND
        - At least one root cause with remediation is identified
        
        Returns:
            True if analysis is actionable, False otherwise
        """
        has_high_confidence = self.confidence.score > 0.7
        has_fixes = len(self.root_causes) > 0
        return has_high_confidence and has_fixes

    def is_critical(self) -> bool:
        """Determine if analysis identifies critical issues.
        
        Business rule: An analysis is critical if:
        - Severity level is HIGH or CRITICAL
        
        Returns:
            True if identified issues are critical, False otherwise
        """
        return self.severity >= Severity.HIGH

    def add_root_cause(self, root_cause: RootCause) -> None:
        """Add a root cause to the analysis.
        
        Args:
            root_cause: RootCause value object to add
            
        Raises:
            TypeError: If root_cause is not a RootCause instance
        """
        if not isinstance(root_cause, RootCause):
            raise TypeError(f"Expected RootCause, got {type(root_cause)}")
        self.root_causes.append(root_cause)

    def remove_root_cause(self, component: str) -> bool:
        """Remove root causes for a specific component.
        
        Args:
            component: Component name to remove root causes for
            
        Returns:
            True if any root causes were removed, False otherwise
        """
        initial_count = len(self.root_causes)
        self.root_causes = [rc for rc in self.root_causes if rc.component != component]
        return len(self.root_causes) < initial_count

    def get_root_causes_for_component(self, component: str) -> list[RootCause]:
        """Get all root causes for a specific component.
        
        Args:
            component: Component name to filter by
            
        Returns:
            List of root causes affecting the specified component
        """
        return [rc for rc in self.root_causes if rc.component == component]

    def mark_resolved(self) -> None:
        """Mark this analysis as resolved.
        
        Indicates that identified issues have been addressed.
        """
        self.is_resolved = True

    def get_remediation_steps(self) -> list[str]:
        """Get ordered list of recommended remediation steps.
        
        Returns:
            List of remediation recommendations from all root causes
        """
        return [rc.remediation for rc in self.root_causes]

    def add_domain_event(self, event: DomainEvent) -> None:
        """Add a domain event to be published after persistence.
        
        Events are stored in the aggregate until explicitly cleared.
        This allows batching multiple events before publishing.
        
        Args:
            event: DomainEvent instance to add
            
        Raises:
            TypeError: If event is not a DomainEvent instance
        """
        if not isinstance(event, DomainEvent):
            raise TypeError(f"Expected DomainEvent, got {type(event)}")
        object.__setattr__(self, "domain_events", self.domain_events + [event])

    def clear_domain_events(self) -> list[DomainEvent]:
        """Clear and return all accumulated domain events.
        
        This method is typically called after the aggregate has been persisted,
        to collect all events for publishing. Events are removed from the aggregate
        to prevent duplicate publishing.
        
        Returns:
            List of accumulated DomainEvent instances
        """
        events = self.domain_events.copy()
        object.__setattr__(self, "domain_events", [])
        return events
    def __str__(self) -> str:
        """Return string representation of log analysis.
        
        Returns:
            Formatted summary of analysis
        """
        status = "Resolved" if self.is_resolved else "Active"
        return (
            f"LogAnalysis(id={self.id}, severity={self.severity.name}, "
            f"confidence={self.confidence}, status={status})"
        )
