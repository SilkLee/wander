"""Severity value object for log analysis domain.

Severity represents the importance level of identified issues in log analysis.
It supports comparison operations for business logic evaluation.
"""

from enum import Enum


class Severity(Enum):
    """Severity level enumeration with comparison support.
    
    Supports ordering: LOW < MEDIUM < HIGH < CRITICAL
    Attributes:
        LOW: Minor issues that don't require immediate action
        MEDIUM: Issues that should be addressed soon
        HIGH: Serious issues requiring prompt attention
        CRITICAL: Critical issues requiring immediate action
    """

    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

    def __lt__(self, other: "Severity") -> bool:
        """Check if this severity is lower than another.
        
        Args:
            other: Another Severity instance to compare with
            
        Returns:
            True if this severity's value is less than other's value
            
        Raises:
            TypeError: If other is not a Severity instance
        """
        if not isinstance(other, Severity):
            raise TypeError(f"Cannot compare Severity with {type(other)}")
        return self.value < other.value

    def __le__(self, other: "Severity") -> bool:
        """Check if this severity is lower than or equal to another.
        
        Args:
            other: Another Severity instance to compare with
            
        Returns:
            True if this severity's value is less than or equal to other's value
            
        Raises:
            TypeError: If other is not a Severity instance
        """
        if not isinstance(other, Severity):
            raise TypeError(f"Cannot compare Severity with {type(other)}")
        return self.value <= other.value

    def __gt__(self, other: "Severity") -> bool:
        """Check if this severity is greater than another.
        
        Args:
            other: Another Severity instance to compare with
            
        Returns:
            True if this severity's value is greater than other's value
            
        Raises:
            TypeError: If other is not a Severity instance
        """
        if not isinstance(other, Severity):
            raise TypeError(f"Cannot compare Severity with {type(other)}")
        return self.value > other.value

    def __ge__(self, other: "Severity") -> bool:
        """Check if this severity is greater than or equal to another.
        
        Args:
            other: Another Severity instance to compare with
            
        Returns:
            True if this severity's value is greater than or equal to other's value
            
        Raises:
            TypeError: If other is not a Severity instance
        """
        if not isinstance(other, Severity):
            raise TypeError(f"Cannot compare Severity with {type(other)}")
        return self.value >= other.value
