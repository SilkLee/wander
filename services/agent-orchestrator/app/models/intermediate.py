from typing import Dict, List

from pydantic import BaseModel, Field


class ParsedLog(BaseModel):
    source: str = Field(description="Log source (ci/runtime/deploy)")
    error_signatures: List[str] = Field(description="Key error signatures")
    stack_fragments: List[str] = Field(description="Stack trace fragments")
    environment: Dict[str, str] = Field(description="Contextual environment")


class Diagnosis(BaseModel):
    root_cause_candidates: List[str] = Field(description="Candidate root causes")
    confidence: float = Field(ge=0.0, le=1.0, description="Diagnosis confidence")
    reasoning: str = Field(description="Short reasoning summary")


class EvidenceBundle(BaseModel):
    citations: List[str] = Field(description="Reference URLs or docs")
    snippets: List[str] = Field(description="Key evidence excerpts")
    relevance_scores: List[float] = Field(description="Relevance scores")


class Remediation(BaseModel):
    steps: List[str] = Field(description="Fix steps")
    risk_notes: List[str] = Field(description="Risks or caveats")
    verification_commands: List[str] = Field(description="Verification commands")
