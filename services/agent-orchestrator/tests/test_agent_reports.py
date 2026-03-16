from pydantic import ValidationError

from app.models.agent_reports import PRSummary, RiskFinding, DependencyRisk, ImpactReport


def test_pr_summary_validation():
    PRSummary(summary="Short summary", key_risks=["touches auth"], actions=["run tests"])


def test_risk_finding_validation():
    RiskFinding(category="security", severity="high", description="Uses eval")


def test_dependency_risk_validation():
    DependencyRisk(package="requests", change_type="upgrade", risk_level="medium")


def test_impact_report_validation():
    ImpactReport(services=["api-gateway"], modules=["auth"], notes="Affects login")


def test_invalid_severity_rejected():
    try:
        RiskFinding(category="security", severity="invalid", description="bad")
    except ValidationError:
        return
    raise AssertionError("Expected ValidationError")
