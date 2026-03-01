"""Output parser adapter implementing ParserPort.

Reuses existing extraction logic from analyzer.py _extract_* methods.
Converts raw agent dict output to domain models (LogAnalysis, Severity, Confidence, RootCause).
"""

import re
from typing import Any, Optional

from app.application.ports import ParserPort
from app.domain.models.confidence import Confidence
from app.domain.models.root_cause import RootCause
from app.domain.models.severity import Severity


class OutputParserAdapter(ParserPort):
    """Adapter parsing agent output into domain models.
    
    This adapter implements the ParserPort interface, handling:
    1. Extraction of structured fields from raw agent dicts
    2. Conversion to domain value objects (Severity, Confidence)
    3. Domain model instantiation with validation
    4. Error handling with clear messages
    
    The parser reuses extraction logic from analyzer.py to maintain consistency.
    """

    def parse_analysis_result(self, raw_result: dict[str, Any]) -> tuple[Severity, Confidence, list[RootCause]]:
        """Parse agent output into domain components.
        
        Converts raw dict from agent (returned by AgentPort) into typed domain objects.
        Performs validation and type conversion at domain boundary.
        
        Args:
            raw_result: Raw dict from agent analysis with keys:
                - root_cause: str - Root cause description
                - severity: str - Severity level (critical/high/medium/low)
                - suggested_fixes: list[str] - List of fix suggestions
                - references: list[str] - Related documentation URLs
                - confidence: float - Confidence score (0.0-1.0)
                - (optional) raw_output: str - Full agent output for extraction fallback
                
        Returns:
            Tuple of (Severity, Confidence, List[RootCause]):
            - severity: Parsed Severity domain object
            - confidence: Parsed Confidence domain object  
            - root_causes: List of RootCause domain objects (minimum 1)
            
        Raises:
            ValueError: If required keys missing or values invalid for domain
            TypeError: If types don't match expected conversion
        """
        try:
            # Extract and validate required fields
            severity = self._parse_severity(raw_result)
            confidence = self._parse_confidence(raw_result)
            root_causes = self._parse_root_causes(raw_result)

            # Ensure we have at least one root cause
            if not root_causes:
                raise ValueError("Parser must identify at least one root cause")

            return severity, confidence, root_causes

        except ValueError as e:
            raise ValueError(f"Parse validation error: {e}")
        except KeyError as e:
            raise ValueError(f"Missing required field in agent result: {e}")
        except Exception as e:
            raise ValueError(
                f"Failed to parse agent output: {type(e).__name__}: {e}"
            )

    def _parse_severity(self, raw_result: dict[str, Any]) -> Severity:
        """Parse severity from raw result dict.
        
        Args:
            raw_result: Raw agent result dict
            
        Returns:
            Severity domain object
            
        Raises:
            ValueError: If severity value is invalid
        """
        severity_str = raw_result.get("severity", "medium").strip().lower()

        # Map string to Severity enum
        severity_map = {
            "critical": Severity.CRITICAL,
            "high": Severity.HIGH,
            "medium": Severity.MEDIUM,
            "low": Severity.LOW,
        }

        if severity_str not in severity_map:
            raise ValueError(
                f"Invalid severity: {severity_str}. "
                f"Must be one of: {list(severity_map.keys())}"
            )

        return severity_map[severity_str]

    def _parse_confidence(self, raw_result: dict[str, Any]) -> Confidence:
        """Parse confidence from raw result dict.
        
        Args:
            raw_result: Raw agent result dict
            
        Returns:
            Confidence domain object
            
        Raises:
            ValueError: If confidence score is invalid
        """
        confidence_raw = raw_result.get("confidence", 0.5)

        # Convert to float if string
        if isinstance(confidence_raw, str):
            try:
                confidence_score = float(confidence_raw)
            except ValueError:
                raise ValueError(
                    f"Confidence must be numeric, got: {confidence_raw}"
                )
        else:
            confidence_score = float(confidence_raw)

        # Clamp to valid range [0.0, 1.0]
        confidence_score = max(0.0, min(1.0, confidence_score))

        return Confidence(score=confidence_score)

    def _parse_root_causes(self, raw_result: dict[str, Any]) -> list[RootCause]:
        """Parse root causes from raw result dict.
        
        Extracts root_cause + suggested_fixes and creates RootCause domain objects.
        Falls back to raw_output if needed.
        
        Args:
            raw_result: Raw agent result dict
            
        Returns:
            List of RootCause domain objects
            
        Raises:
            ValueError: If root cause extraction fails or produces no results
        """
        root_causes: list[RootCause] = []

        try:
            # Primary: Use root_cause field and suggested_fixes
            root_cause_desc = raw_result.get("root_cause", "").strip()
            suggested_fixes = raw_result.get("suggested_fixes", [])

            if root_cause_desc:
                # Determine component from root cause text or use default
                component = self._extract_component_from_text(root_cause_desc)

                # Use first fix as remediation, or generate default
                remediation = (
                    suggested_fixes[0]
                    if suggested_fixes
                    else "Review and address the identified root cause"
                )

                root_causes.append(
                    RootCause(
                        description=root_cause_desc,
                        component=component,
                        remediation=remediation,
                    )
                )

            # Secondary: Extract additional fixes as root causes
            for fix in suggested_fixes[1:]:  # Skip first (already used as remediation)
                if fix.strip():
                    root_causes.append(
                        RootCause(
                            description=f"Action item: {fix.strip()}",
                            component="system",
                            remediation=fix.strip(),
                        )
                    )

            # Tertiary: Fallback to raw_output parsing if no causes found
            if not root_causes:
                raw_output = raw_result.get("raw_output", "")
                if raw_output:
                    fallback_cause = self._extract_root_cause_from_output(raw_output)
                    if fallback_cause:
                        root_causes.append(fallback_cause)

            if not root_causes:
                raise ValueError(
                    "Unable to extract root cause from agent result. "
                    "Check raw_result structure."
                )

            return root_causes

        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"Failed to parse root causes: {e}")

    def _extract_component_from_text(self, text: str) -> str:
        """Extract component name from text using heuristics.
        
        Args:
            text: Text to search for component hints
            
        Returns:
            Component name (e.g., "build", "deploy", "database") or "unknown"
        """
        text_lower = text.lower()

        # Component keywords
        components = [
            "build",
            "deploy",
            "database",
            "network",
            "storage",
            "cache",
            "auth",
            "api",
            "queue",
            "service",
        ]

        for component in components:
            if component in text_lower:
                return component

        return "unknown"

    def _extract_root_cause_from_output(self, output: str) -> Optional[RootCause]:
        """Extract root cause from raw agent output as fallback.
        
        Reuses pattern matching logic from analyzer.py _extract_root_cause.
        
        Args:
            output: Raw agent output string
            
        Returns:
            RootCause object if found, None otherwise
        """
        try:
            lines = output.split("\n")

            for i, line in enumerate(lines):
                if "root cause" in line.lower():
                    cause_text = ""
                    if ":" in line:
                        cause_text = line.split(":", 1)[1].strip()
                    elif i + 1 < len(lines):
                        cause_text = lines[i + 1].strip()

                    if cause_text:
                        component = self._extract_component_from_text(cause_text)
                        return RootCause(
                            description=cause_text[:200],
                            component=component,
                            remediation="Review and address the identified issue",
                        )

            # Fallback: Use first meaningful line
            for line in lines:
                if line.strip() and len(line.strip()) > 20:
                    component = self._extract_component_from_text(line)
                    return RootCause(
                        description=line.strip()[:200],
                        component=component,
                        remediation="Investigate the issue further",
                    )

            return None

        except Exception:
            return None
