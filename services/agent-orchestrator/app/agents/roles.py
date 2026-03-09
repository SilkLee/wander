from enum import Enum
import re
from typing import Dict, List

from app.models.intermediate import Diagnosis, EvidenceBundle, ParsedLog, Remediation


class AgentRole(str, Enum):
    PARSER = "parser"
    DIAGNOSTICIAN = "diagnostician"
    RETRIEVER = "retriever"
    REMEDIATOR = "remediator"


async def parse_log(inputs: Dict) -> ParsedLog:
    raw_log: str = inputs.get("log_content", "")
    error_sigs: List[str] = re.findall(r"(?:ERROR|FATAL|CRITICAL)[:\s]+(.+)", raw_log)
    stack_frags: List[str] = re.findall(r"[\w/]+\.py:\d+", raw_log)

    return ParsedLog(
        source=inputs.get("log_type", "build"),
        error_signatures=error_sigs if error_sigs else ["unknown"],
        stack_fragments=stack_frags,
        environment={"repository": inputs.get("context", {}).get("repository", "")},
    )


async def diagnose(parsed: ParsedLog) -> Diagnosis:
    return Diagnosis(
        root_cause_candidates=parsed.error_signatures or ["unknown"],
        confidence=0.6,
        reasoning="Stub diagnosis based on error signatures",
    )


async def retrieve_evidence(diagnosis: Diagnosis) -> EvidenceBundle:
    return EvidenceBundle(
        citations=["https://docs.example.com/stub"],
        snippets=["Stub evidence for: " + ", ".join(diagnosis.root_cause_candidates)],
        relevance_scores=[0.5],
    )


async def remediate(diagnosis: Diagnosis, evidence: EvidenceBundle) -> Remediation:
    return Remediation(
        steps=["Review error: " + ", ".join(diagnosis.root_cause_candidates)],
        risk_notes=["Stub remediation - verify before applying"],
        verification_commands=["echo stub-verification"],
    )
