import pytest
from pydantic import ValidationError

from app.models.incident import ChangeImpact, IncidentReport, MetricsSummary


def test_incident_report_valid():
    report = IncidentReport(
        root_cause="redis outage",
        evidence=["redis timeout", "connection refused"],
        remediation=["restart redis", "increase pool size"],
        rollback=["revert deploy"],
    )
    assert report.root_cause == "redis outage"
    assert len(report.evidence) == 2
    assert len(report.remediation) == 2
    assert len(report.rollback) == 1


def test_incident_report_rejects_empty_root_cause():
    with pytest.raises(ValidationError):
        IncidentReport(
            root_cause="",
            evidence=["timeout"],
            remediation=["restart"],
            rollback=["revert"],
        )


def test_incident_report_rejects_empty_evidence():
    with pytest.raises(ValidationError):
        IncidentReport(
            root_cause="redis outage",
            evidence=[],
            remediation=["restart"],
            rollback=["revert"],
        )


def test_incident_report_rejects_empty_remediation():
    with pytest.raises(ValidationError):
        IncidentReport(
            root_cause="redis outage",
            evidence=["timeout"],
            remediation=[],
            rollback=["revert"],
        )


def test_incident_report_rejects_empty_rollback():
    with pytest.raises(ValidationError):
        IncidentReport(
            root_cause="redis outage",
            evidence=["timeout"],
            remediation=["restart"],
            rollback=[],
        )


def test_metrics_summary_valid():
    summary = MetricsSummary(
        error_rate=0.15,
        latency_p99_ms=450.0,
        anomalies=["spike in 5xx errors"],
    )
    assert summary.error_rate == 0.15
    assert summary.latency_p99_ms == 450.0
    assert summary.anomalies == ["spike in 5xx errors"]


def test_metrics_summary_defaults():
    summary = MetricsSummary()
    assert summary.error_rate == 0.0
    assert summary.latency_p99_ms == 0.0
    assert summary.anomalies == []


def test_metrics_summary_rejects_negative_error_rate():
    with pytest.raises(ValidationError):
        MetricsSummary(error_rate=-0.1)


def test_metrics_summary_rejects_negative_latency():
    with pytest.raises(ValidationError):
        MetricsSummary(latency_p99_ms=-1.0)


def test_change_impact_valid():
    impact = ChangeImpact(
        files_changed=["src/redis.py", "src/config.py"],
        risk_level="high",
        summary="Modified Redis connection handling",
    )
    assert len(impact.files_changed) == 2
    assert impact.risk_level == "high"
    assert "Redis" in impact.summary


def test_change_impact_defaults():
    impact = ChangeImpact(
        risk_level="low",
        summary="Minor config change",
    )
    assert impact.files_changed == []


def test_change_impact_rejects_invalid_risk_level():
    with pytest.raises(ValidationError):
        ChangeImpact(
            risk_level="extreme",
            summary="bad risk level",
        )


def test_change_impact_rejects_empty_summary():
    with pytest.raises(ValidationError):
        ChangeImpact(
            risk_level="low",
            summary="",
        )
