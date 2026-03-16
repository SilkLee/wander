import asyncio


from app.agents.incident_roles import change_impact, coordinator, metrics_analyzer
from app.models.incident import ChangeImpact, IncidentReport, MetricsSummary


def test_metrics_analyzer_returns_metrics_summary():

    async def run():
        return await metrics_analyzer(
            {
                "service": "api-gateway",
                "error_rate": 0.25,
                "latency_p99_ms": 800.0,
                "alerts": ["5xx spike", "latency threshold breach"],
            }
        )

    result = asyncio.run(run())
    assert isinstance(result, MetricsSummary)
    assert result.error_rate >= 0.0
    assert result.latency_p99_ms >= 0.0
    assert isinstance(result.anomalies, list)


def test_change_impact_returns_change_impact():

    async def run():
        return await change_impact(
            {
                "deploy_id": "deploy-42",
                "files_changed": ["src/redis.py", "src/config.py"],
                "commit_message": "update redis pool settings",
            }
        )

    result = asyncio.run(run())
    assert isinstance(result, ChangeImpact)
    assert result.risk_level in ("low", "medium", "high", "critical")
    assert result.summary.strip() != ""
    assert isinstance(result.files_changed, list)


def test_coordinator_returns_incident_report():

    async def run():
        metrics = MetricsSummary(
            error_rate=0.25,
            latency_p99_ms=800.0,
            anomalies=["5xx spike"],
        )
        impact = ChangeImpact(
            files_changed=["src/redis.py"],
            risk_level="high",
            summary="Modified Redis connection handling",
        )
        return await coordinator(metrics, impact)

    result = asyncio.run(run())
    assert isinstance(result, IncidentReport)
    assert result.root_cause.strip() != ""
    assert len(result.evidence) >= 1
    assert len(result.remediation) >= 1
    assert len(result.rollback) >= 1


def test_full_incident_pipeline():

    async def run():
        metrics = await metrics_analyzer(
            {
                "service": "payment-service",
                "error_rate": 0.40,
                "latency_p99_ms": 1200.0,
                "alerts": ["timeout cascade"],
            }
        )
        impact = await change_impact(
            {
                "deploy_id": "deploy-99",
                "files_changed": ["src/payments.py"],
                "commit_message": "refactor payment retry logic",
            }
        )
        report = await coordinator(metrics, impact)
        return metrics, impact, report

    metrics, impact, report = asyncio.run(run())
    assert isinstance(metrics, MetricsSummary)
    assert isinstance(impact, ChangeImpact)
    assert isinstance(report, IncidentReport)


def test_metrics_analyzer_handles_empty_alerts():

    async def run():
        return await metrics_analyzer(
            {
                "service": "web-frontend",
                "error_rate": 0.01,
                "latency_p99_ms": 50.0,
                "alerts": [],
            }
        )

    result = asyncio.run(run())
    assert isinstance(result, MetricsSummary)
    assert result.anomalies == []


def test_change_impact_handles_no_files():

    async def run():
        return await change_impact(
            {
                "deploy_id": "deploy-0",
                "files_changed": [],
                "commit_message": "config-only change",
            }
        )

    result = asyncio.run(run())
    assert isinstance(result, ChangeImpact)
    assert result.files_changed == []
