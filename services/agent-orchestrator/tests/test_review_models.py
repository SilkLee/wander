from pydantic import ValidationError

from app.models.review import PRRiskReport, ReviewComment, ReviewSummary


def test_pr_risk_report_validation():
    PRRiskReport(
        risk_level="medium",
        impacted_areas=["ci", "db"],
        checks=["run full integration"],
        rationale="Touches migration + db config",
    )


def test_review_comment_validation():
    ReviewComment(
        file="services/api/handler.py",
        line=42,
        severity="warning",
        message="Missing input validation",
        suggestion="Add pydantic validation",
    )


def test_review_summary_validation():
    ReviewSummary(
        summary="Overall OK",
        comments=[],
        severity_breakdown={"warning": 1},
    )


def test_invalid_risk_level_rejected():
    try:
        PRRiskReport(
            risk_level="invalid",
            impacted_areas=[],
            checks=[],
            rationale="",
        )
    except ValidationError:
        return
    raise AssertionError("Expected ValidationError")
