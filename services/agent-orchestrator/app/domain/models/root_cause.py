"""Root cause value object for log analysis domain.

RootCause represents a potential root cause of issues identified in logs.
It is an immutable value object capturing the analysis result.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class RootCause:
    """Immutable root cause value object representing identified causes.
    
    Represents a potential root cause of issues discovered during log analysis,
    including description, component affected, and remediation guidance.
    
    Attributes:
        description: Human-readable description of the root cause
        component: The system component where root cause was identified
        remediation: Recommended action to fix the root cause
        
    Raises:
        ValueError: If any required field is empty or whitespace-only
    """

    description: str
    component: str
    remediation: str

    def __post_init__(self) -> None:
        """Validate root cause fields are not empty.
        
        Raises:
            ValueError: If description, component, or remediation are empty/whitespace
        """
        if not self.description or not self.description.strip():
            raise ValueError("Root cause description cannot be empty")
        if not self.component or not self.component.strip():
            raise ValueError("Root cause component cannot be empty")
        if not self.remediation or not self.remediation.strip():
            raise ValueError("Root cause remediation cannot be empty")

    def __str__(self) -> str:
        """Return string representation of root cause.
        
        Returns:
            Formatted root cause summary
        """
        return f"RootCause({self.component}): {self.description}"

    def __repr__(self) -> str:
        """Return detailed representation of root cause.
        
        Returns:
            Detailed string representation for debugging
        """
        return (
            f"RootCause(description={self.description!r}, "
            f"component={self.component!r}, remediation={self.remediation!r})"
        )

    @property
    def summary(self) -> str:
        """Get a summary of the root cause with remediation.
        
        Returns:
            Formatted string with description and remediation guidance
        """
        return f"{self.description} → {self.remediation}"
