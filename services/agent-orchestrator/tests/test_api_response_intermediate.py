import json
from typing import Any, Dict

from app.models.requests import LogAnalysisResponse


def _make_response(**overrides: Any) -> LogAnalysisResponse:
    defaults: Dict[str, Any] = {
        "analysis_id": "test-id-001",
        "root_cause": "Connection timeout to database",
        "severity": "high",
        "suggested_fixes": ["Increase connection pool size"],
        "references": [],
        "confidence": 0.85,
    }
    defaults.update(overrides)
    return LogAnalysisResponse(**defaults)


class TestIntermediateSummaryFieldExists:
    def test_has_intermediate_summary_in_model_fields(self):
        assert "intermediate_summary" in LogAnalysisResponse.model_fields

    def test_field_type_accepts_dict(self):
        resp = _make_response(intermediate_summary={"key": "value"})
        assert isinstance(resp.intermediate_summary, dict)


class TestIntermediateSummaryDefault:
    def test_defaults_to_empty_dict(self):
        resp = _make_response()
        assert resp.intermediate_summary == {}

    def test_default_is_dict_type(self):
        resp = _make_response()
        assert isinstance(resp.intermediate_summary, dict)

    def test_each_instance_gets_own_default(self):
        resp1 = _make_response()
        resp2 = _make_response()
        resp1.intermediate_summary["mutated"] = True
        assert "mutated" not in resp2.intermediate_summary


class TestIntermediateSummaryPopulated:
    def test_accepts_populated_dict(self):
        summary = {
            "severity": "high",
            "confidence_score": 0.9,
            "root_cause_count": 2,
            "is_actionable": True,
            "is_critical": True,
        }
        resp = _make_response(intermediate_summary=summary)
        assert resp.intermediate_summary == summary

    def test_preserves_nested_structure(self):
        summary = {
            "severity": "medium",
            "details": {"step": "parse_log", "duration_ms": 42},
        }
        resp = _make_response(intermediate_summary=summary)
        assert resp.intermediate_summary["details"]["step"] == "parse_log"

    def test_preserves_numeric_values(self):
        summary = {"confidence_score": 0.95, "root_cause_count": 3}
        resp = _make_response(intermediate_summary=summary)
        assert resp.intermediate_summary["confidence_score"] == 0.95
        assert resp.intermediate_summary["root_cause_count"] == 3

    def test_preserves_boolean_values(self):
        summary = {"is_actionable": False, "is_critical": True}
        resp = _make_response(intermediate_summary=summary)
        assert resp.intermediate_summary["is_actionable"] is False
        assert resp.intermediate_summary["is_critical"] is True


class TestIntermediateSummarySerialization:
    def test_model_dump_includes_intermediate_summary(self):
        resp = _make_response()
        data = resp.model_dump()
        assert "intermediate_summary" in data
        assert data["intermediate_summary"] == {}

    def test_model_dump_with_populated_summary(self):
        summary = {"severity": "low", "confidence_score": 0.5}
        resp = _make_response(intermediate_summary=summary)
        data = resp.model_dump()
        assert data["intermediate_summary"] == summary

    def test_model_dump_roundtrip(self):
        summary = {
            "severity": "critical",
            "confidence_score": 0.99,
            "root_cause_count": 1,
            "is_actionable": True,
            "is_critical": True,
        }
        resp = _make_response(intermediate_summary=summary)
        data = resp.model_dump()
        reconstructed = LogAnalysisResponse(**data)
        assert reconstructed == resp
        assert reconstructed.intermediate_summary == summary

    def test_json_serialization_includes_field(self):
        summary = {"severity": "high", "confidence_score": 0.8}
        resp = _make_response(intermediate_summary=summary)
        json_str = resp.model_dump_json()
        parsed = json.loads(json_str)
        assert "intermediate_summary" in parsed
        assert parsed["intermediate_summary"]["severity"] == "high"

    def test_json_roundtrip_empty_summary(self):
        resp = _make_response()
        json_str = resp.model_dump_json()
        parsed = json.loads(json_str)
        reconstructed = LogAnalysisResponse(**parsed)
        assert reconstructed.intermediate_summary == {}
