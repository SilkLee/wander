"""Log analyzer agent using LangChain."""

import uuid
from typing import Any, Dict, List

from langchain.tools import BaseTool

from app.agents.base import BaseAgent


class LogAnalyzerAgent(BaseAgent):
    """
    Agent for analyzing build/deploy logs and identifying root causes.
    
    Uses LangChain tools to:
    1. Search knowledge base (RAG) for similar failures
    2. Extract error patterns from logs
    3. Provide actionable fix suggestions
    """

    def get_tools(self) -> List[BaseTool]:
        """
        Get tools for log analysis.
        
        Returns:
            List of tools including knowledge base search
        """
        from app.tools.knowledge_base import KnowledgeBaseTool
        
        return [
            KnowledgeBaseTool(),
        ]

    def get_system_prompt(self) -> str:
        """
        Get system prompt for log analyzer.
        
        Returns:
            Detailed system prompt for log analysis
        """
        return """You are an expert DevOps engineer specializing in build and deployment failure analysis.

Your task is to analyze logs and identify:
1. **Root cause** - The fundamental reason for failure (not just symptoms)
2. **Severity** - Impact level (critical/high/medium/low)
3. **Fix suggestions** - Concrete, actionable steps to resolve the issue
4. **References** - Related documentation or similar issues

When analyzing logs:
- Extract error messages, stack traces, and failure signals
- Use the knowledge base tool to search for similar failures
- Consider the context (repo, branch, environment, recent changes)
- Provide step-by-step fix instructions
- Include confidence score (0.0-1.0) based on evidence quality

Be concise but thorough. Developers need quick, accurate diagnosis."""

    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute log analysis workflow.
        
        Args:
            inputs: Must contain:
                - log_content: str - Log text to analyze
                - log_type: str - Type (build/deploy/runtime)
                - context: dict - Additional metadata
        
        Returns:
            Dict with:
                - analysis_id: str
                - root_cause: str
                - severity: str
                - suggested_fixes: List[str]
                - references: List[str]
                - confidence: float
        """
        # Generate analysis ID
        analysis_id = str(uuid.uuid4())
        
        # Extract inputs
        log_content = inputs.get("log_content", "")
        log_type = inputs.get("log_type", "build")
        context = inputs.get("context", {})
        
        # Build agent input
        agent_input = f"""Analyze this {log_type} log:

LOG CONTENT:
{log_content[:5000]}  # Truncate to prevent token overflow

CONTEXT:
{context}

Provide:
1. Root cause (one sentence)
2. Severity (critical/high/medium/low)
3. Suggested fixes (numbered list)
4. References (URLs or doc names)
5. Confidence score (0.0-1.0)
"""
        
        # Create executor
        executor = self.create_executor()
        
        # Execute agent
        result = await executor.ainvoke({"input": agent_input})
        
        # Parse agent output
        output = result.get("output", "")
        intermediate_steps = result.get("intermediate_steps", [])
        
        # Extract structured data from output (simplified parsing)
        # In production, use structured output or better parsing
        root_cause = self._extract_root_cause(output)
        severity = self._extract_severity(output)
        suggested_fixes = self._extract_fixes(output)
        references = self._extract_references(output, intermediate_steps)
        confidence = self._extract_confidence(output)
        
        return {
            "analysis_id": analysis_id,
            "root_cause": root_cause,
            "severity": severity,
            "suggested_fixes": suggested_fixes,
            "references": references,
            "confidence": confidence,
            "raw_output": output,  # For debugging
        }

    def _extract_root_cause(self, output: str) -> str:
        """Extract root cause from agent output."""
        # Simple extraction - look for "Root cause:" pattern
        lines = output.split("\n")
        for i, line in enumerate(lines):
            if "root cause" in line.lower():
                # Take next line or same line after colon
                if ":" in line:
                    return line.split(":", 1)[1].strip()
                elif i + 1 < len(lines):
                    return lines[i + 1].strip()
        return output[:200]  # Fallback: first 200 chars

    def _extract_severity(self, output: str) -> str:
        """Extract severity from agent output."""
        output_lower = output.lower()
        if "critical" in output_lower:
            return "critical"
        elif "high" in output_lower:
            return "high"
        elif "medium" in output_lower:
            return "medium"
        elif "low" in output_lower:
            return "low"
        return "medium"  # Default

    def _extract_fixes(self, output: str) -> List[str]:
        """Extract suggested fixes from agent output."""
        fixes = []
        lines = output.split("\n")
        
        # Look for numbered lists or bullet points after "fix" keyword
        capture = False
        for line in lines:
            line_stripped = line.strip()
            if "fix" in line.lower() or "suggestion" in line.lower():
                capture = True
                continue
            
            if capture and line_stripped:
                # Stop at next section header
                if line_stripped.endswith(":") or "reference" in line.lower():
                    break
                # Extract numbered or bulleted items
                if line_stripped[0].isdigit() or line_stripped.startswith(("-", "*", "•")):
                    # Remove numbering/bullets
                    clean_line = line_stripped.lstrip("0123456789.-*• ")
                    if clean_line:
                        fixes.append(clean_line)
        
        return fixes if fixes else ["Review logs and check recent changes"]

    def _extract_references(self, output: str, intermediate_steps: List) -> List[str]:
        """Extract references from agent output and tool results."""
        references = []
        
        # From output text
        lines = output.split("\n")
        for line in lines:
            if "http" in line or "docs." in line:
                # Extract URLs
                words = line.split()
                for word in words:
                    if word.startswith("http") or "docs." in word:
                        references.append(word.strip(",.()"))
        
        # From knowledge base tool results
        for action, observation in intermediate_steps:
            if "knowledge" in str(action).lower():
                # Parse KB tool output for references
                if isinstance(observation, str) and "http" in observation:
                    words = observation.split()
                    for word in words:
                        if word.startswith("http"):
                            references.append(word.strip(",.()"))
        
        return list(set(references))  # Deduplicate

    def _extract_confidence(self, output: str) -> float:
        """Extract confidence score from agent output."""
        import re
        
        # Look for confidence score patterns
        patterns = [
            r"confidence[:\s]+([0-9.]+)",
            r"confidence score[:\s]+([0-9.]+)",
            r"\(([0-9.]+)\s*confidence\)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, output.lower())
            if match:
                try:
                    score = float(match.group(1))
                    return max(0.0, min(1.0, score))  # Clamp to [0, 1]
                except ValueError:
                    pass
        
        # Default confidence based on output quality
        if len(output) > 500 and "error" in output.lower():
            return 0.75
        elif len(output) > 200:
            return 0.6
        return 0.4
