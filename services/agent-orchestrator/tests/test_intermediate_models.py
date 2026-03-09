"""Tests for intermediate DTOs used between LangGraph nodes.

Covers: construction, validation, edge cases, serialization, and package exports.
"""

import pytest
from pydantic import ValidationError

from app.models.intermediate import Diagnosis, EvidenceBundle, ParsedLog, Remediation


# ---------------------------------------------------------------------------
# ParsedLog
# ---------------------------------------------------------------------------


class TestParsedLog:
    """ParsedLog DTO validation and serialization."""

    def test_valid_construction(self):
        log = ParsedLog(
            source="ci",
            error_signatures=["timeout expired"],
            stack_fragments=["database.py:142"],
            environment={"service": "api"},
        )
        assert log.source == "ci"
        assert log.error_signatures == ["timeout expired"]
        assert log.stack_fragments == ["database.py:142"]
        assert log.environment == {"service": "api"}

    def test_empty_lists_accepted(self):
        log = ParsedLog(
            source="runtime",
            error_signatures=[],
            stack_fragments=[],
            environment={},
        )
        assert log.error_signatures == []
        assert log.stack_fragments == []
        assert log.environment == {}

    def test_multiple_entries(self):
        log = ParsedLog(
            source="deploy",
            error_signatures=["OOM", "segfault", "SIGKILL"],
            stack_fragments=["main.py:10", "lib.py:55"],
            environment={"node": "worker-1", "region": "us-east-1"},
        )
        assert len(log.error_signatures) == 3
        assert len(log.environment) == 2

    def test_rejects_missing_source(self):
        with pytest.raises(ValidationError):
            ParsedLog(
                error_signatures=["err"],
                stack_fragments=["f.py:1"],
                environment={},
            )

    def test_rejects_missing_error_signatures(self):
        with pytest.raises(ValidationError):
            ParsedLog(
                source="ci",
                stack_fragments=["f.py:1"],
                environment={},
            )

    def test_model_dump_roundtrip(self):
        log = ParsedLog(
            source="ci",
            error_signatures=["err"],
            stack_fragments=["f.py:1"],
            environment={"k": "v"},
        )
        data = log.model_dump()
        reconstructed = ParsedLog(**data)
        assert reconstructed == log


# ---------------------------------------------------------------------------
# Diagnosis
# ---------------------------------------------------------------------------


class TestDiagnosis:
    """Diagnosis DTO validation and confidence bounds."""

    def test_valid_construction(self):
        diag = Diagnosis(
            root_cause_candidates=["DB connection timeout"],
            confidence=0.7,
            reasoning="Connection to DB failed during deploy",
        )
        assert diag.confidence == 0.7
        assert len(diag.root_cause_candidates) == 1

    def test_confidence_lower_bound_zero(self):
        diag = Diagnosis(
            root_cause_candidates=["unknown"],
            confidence=0.0,
            reasoning="No idea",
        )
        assert diag.confidence == 0.0

    def test_confidence_upper_bound_one(self):
        diag = Diagnosis(
            root_cause_candidates=["certain cause"],
            confidence=1.0,
            reasoning="Absolutely sure",
        )
        assert diag.confidence == 1.0

    def test_rejects_confidence_above_one(self):
        with pytest.raises(ValidationError):
            Diagnosis(
                root_cause_candidates=["x"],
                confidence=1.5,
                reasoning="bad",
            )

    def test_rejects_negative_confidence(self):
        with pytest.raises(ValidationError):
            Diagnosis(
                root_cause_candidates=["x"],
                confidence=-0.1,
                reasoning="bad",
            )

    def test_rejects_missing_reasoning(self):
        with pytest.raises(ValidationError):
            Diagnosis(
                root_cause_candidates=["x"],
                confidence=0.5,
            )

    def test_multiple_candidates(self):
        diag = Diagnosis(
            root_cause_candidates=["cause A", "cause B", "cause C"],
            confidence=0.4,
            reasoning="Multiple possibilities",
        )
        assert len(diag.root_cause_candidates) == 3

    def test_model_dump_roundtrip(self):
        diag = Diagnosis(
            root_cause_candidates=["timeout"],
            confidence=0.85,
            reasoning="High latency observed",
        )
        data = diag.model_dump()
        reconstructed = Diagnosis(**data)
        assert reconstructed == diag


# ---------------------------------------------------------------------------
# EvidenceBundle
# ---------------------------------------------------------------------------


class TestEvidenceBundle:
    """EvidenceBundle DTO validation."""

    def test_valid_construction(self):
        bundle = EvidenceBundle(
            citations=["https://docs.example.com/db"],
            snippets=["timeout expired"],
            relevance_scores=[0.8],
        )
        assert bundle.citations == ["https://docs.example.com/db"]

    def test_empty_bundle(self):
        bundle = EvidenceBundle(
            citations=[],
            snippets=[],
            relevance_scores=[],
        )
        assert bundle.citations == []
        assert bundle.snippets == []
        assert bundle.relevance_scores == []

    def test_multiple_evidence_items(self):
        bundle = EvidenceBundle(
            citations=["url1", "url2"],
            snippets=["snippet1", "snippet2"],
            relevance_scores=[0.9, 0.7],
        )
        assert len(bundle.citations) == 2
        assert len(bundle.relevance_scores) == 2

    def test_rejects_missing_citations(self):
        with pytest.raises(ValidationError):
            EvidenceBundle(
                snippets=["snip"],
                relevance_scores=[0.5],
            )

    def test_model_dump_roundtrip(self):
        bundle = EvidenceBundle(
            citations=["ref1"],
            snippets=["evidence text"],
            relevance_scores=[0.95],
        )
        data = bundle.model_dump()
        reconstructed = EvidenceBundle(**data)
        assert reconstructed == bundle


# ---------------------------------------------------------------------------
# Remediation
# ---------------------------------------------------------------------------


class TestRemediation:
    """Remediation DTO validation."""

    def test_valid_construction(self):
        rem = Remediation(
            steps=["Check DB network ACL"],
            risk_notes=["May require infra change"],
            verification_commands=["psql -h 10.0.1.50 -p 5432"],
        )
        assert rem.steps == ["Check DB network ACL"]
        assert len(rem.risk_notes) == 1
        assert len(rem.verification_commands) == 1

    def test_empty_lists_accepted(self):
        rem = Remediation(
            steps=[],
            risk_notes=[],
            verification_commands=[],
        )
        assert rem.steps == []

    def test_multi_step_remediation(self):
        rem = Remediation(
            steps=["Stop service", "Apply migration", "Restart service"],
            risk_notes=["Downtime required", "Rollback plan needed"],
            verification_commands=["curl /health", "psql -c SELECT"],
        )
        assert len(rem.steps) == 3
        assert len(rem.risk_notes) == 2
        assert len(rem.verification_commands) == 2

    def test_rejects_missing_steps(self):
        with pytest.raises(ValidationError):
            Remediation(
                risk_notes=["note"],
                verification_commands=["cmd"],
            )

    def test_model_dump_roundtrip(self):
        rem = Remediation(
            steps=["fix it"],
            risk_notes=["risky"],
            verification_commands=["check"],
        )
        data = rem.model_dump()
        reconstructed = Remediation(**data)
        assert reconstructed == rem


# ---------------------------------------------------------------------------
# Package-level imports (app.models.__init__)
# ---------------------------------------------------------------------------


class TestPackageExports:
    """Verify intermediate DTOs are exported from app.models."""

    def test_parsedlog_importable_from_package(self):
        from app.models import ParsedLog as PL

        assert PL is ParsedLog

    def test_diagnosis_importable_from_package(self):
        from app.models import Diagnosis as D

        assert D is Diagnosis

    def test_evidence_bundle_importable_from_package(self):
        from app.models import EvidenceBundle as EB

        assert EB is EvidenceBundle

    def test_remediation_importable_from_package(self):
        from app.models import Remediation as R

        assert R is Remediation
