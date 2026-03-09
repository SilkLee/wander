from app.models.requests import LogAnalysisResponse


def test_response_contains_stability_fields():
    response = LogAnalysisResponse(
        analysis_id="id",
        root_cause="rc",
        severity="high",
        suggested_fixes=["fix"],
        references=[],
        confidence=0.5,
        intermediate_summary={"errors": [{"node": "diagnose"}]},
    )
    assert "errors" in response.intermediate_summary
