from typing import Any

from app.models.incident import ChangeImpact, IncidentReport, MetricsSummary


async def metrics_analyzer(inputs: dict[str, Any]) -> MetricsSummary:
    alerts: list[str] = inputs.get("alerts", [])
    return MetricsSummary(
        error_rate=float(inputs.get("error_rate", 0.0)),
        latency_p99_ms=float(inputs.get("latency_p99_ms", 0.0)),
        anomalies=alerts,
    )


async def change_impact(inputs: dict[str, Any]) -> ChangeImpact:
    files: list[str] = inputs.get("files_changed", [])
    file_count = len(files)
    if file_count == 0:
        risk = "low"
    elif file_count <= 3:
        risk = "medium"
    else:
        risk = "high"

    commit_msg: str = inputs.get("commit_message", "unknown change")
    return ChangeImpact(
        files_changed=files,
        risk_level=risk,
        summary=f"Deploy {inputs.get('deploy_id', 'unknown')}: {commit_msg}",
    )


async def coordinator(metrics: MetricsSummary, impact: ChangeImpact) -> IncidentReport:
    anomaly_detail = ", ".join(metrics.anomalies) if metrics.anomalies else "no anomalies"

    root_cause = (
        f"Service degradation detected — error_rate={metrics.error_rate:.2f}, "
        f"p99={metrics.latency_p99_ms:.0f}ms. "
        f"Risk level: {impact.risk_level}. {impact.summary}"
    )

    evidence = [
        f"error_rate={metrics.error_rate}",
        f"latency_p99_ms={metrics.latency_p99_ms}",
        f"anomalies: {anomaly_detail}",
        f"files_changed: {impact.files_changed}",
    ]

    remediation = [
        f"Investigate root cause in changed files: {impact.files_changed}",
        f"Review anomalies: {anomaly_detail}",
    ]

    rollback = [
        f"Rollback deployment affecting: {', '.join(impact.files_changed) or 'config-only'}",
    ]

    return IncidentReport(
        root_cause=root_cause,
        evidence=evidence,
        remediation=remediation,
        rollback=rollback,
    )
