from typing import Any, Dict, List, Optional

from app.models.review import PRRiskReport, ReviewComment, ReviewSummary


async def diff_parser(inputs: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "diff": inputs.get("diff", ""),
        "context": inputs.get("context", {}),
        "standards": inputs.get("coding_standards", ""),
    }


async def risk_analyst(parsed: Dict[str, Any]) -> PRRiskReport:
    return PRRiskReport(
        risk_level="medium",
        impacted_areas=["ci"],
        checks=["run integration tests"],
        rationale="Touches CI config",
    )


async def reviewer(parsed: Dict[str, Any]) -> List[ReviewComment]:
    return [
        ReviewComment(
            file="unknown",
            line=1,
            severity="info",
            message="Review diff for style consistency",
            suggestion="Apply project formatting",
        )
    ]


async def summarizer(payload: Dict[str, Any]) -> Dict[str, Any]:
    report: Optional[PRRiskReport] = payload.get("report")
    comments: List[ReviewComment] = payload.get("comments", [])
    summary = ReviewSummary(
        summary="Review complete",
        comments=comments,
        severity_breakdown={"info": len(comments)},
    )
    return {
        "analysis": summary.summary,
        "summary": summary,
        "report": report,
    }
