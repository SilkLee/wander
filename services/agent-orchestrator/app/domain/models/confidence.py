"""Confidence value object for log analysis domain.

Confidence represents the certainty level of analysis results.
It is an immutable value object with validation for the range [0.0, 1.0].
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Confidence:
    """Immutable confidence value object representing certainty level.
    
    Confidence is expressed as a probability between 0.0 and 1.0, where:
    - 0.0 represents complete uncertainty
    - 1.0 represents complete certainty
    
    Attributes:
        score: Probability score in range [0.0, 1.0]
        
    Raises:
        ValueError: If score is not in valid range [0.0, 1.0]
    """

    score: float

    def __post_init__(self) -> None:
        """Validate confidence score is within acceptable range.
        
        Raises:
            ValueError: If score is not between 0.0 and 1.0 (inclusive)
        """
        if not (0.0 <= self.score <= 1.0):
            raise ValueError(
                f"Confidence score must be between 0.0 and 1.0, got {self.score}"
            )

    def __str__(self) -> str:
        """Return string representation of confidence.
        
        Returns:
            Formatted confidence percentage (e.g., "85.5%")
        """
        return f"{self.score * 100:.1f}%"

    def is_high(self, threshold: float = 0.7) -> bool:
        """Check if confidence exceeds the given threshold.
        
        Args:
            threshold: Confidence threshold to compare against (default 0.7)
            
        Returns:
            True if confidence score is greater than threshold
            
        Raises:
            ValueError: If threshold is not in valid range [0.0, 1.0]
        """
        if not (0.0 <= threshold <= 1.0):
            raise ValueError(
                f"Threshold must be between 0.0 and 1.0, got {threshold}"
            )
        return self.score > threshold

    def is_low(self, threshold: float = 0.3) -> bool:
        """Check if confidence is below the given threshold.
        
        Args:
            threshold: Confidence threshold to compare against (default 0.3)
            
        Returns:
            True if confidence score is less than threshold
            
        Raises:
            ValueError: If threshold is not in valid range [0.0, 1.0]
        """
        if not (0.0 <= threshold <= 1.0):
            raise ValueError(
                f"Threshold must be between 0.0 and 1.0, got {threshold}"
            )
        return self.score < threshold
