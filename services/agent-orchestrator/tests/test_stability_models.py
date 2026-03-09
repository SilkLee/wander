from pydantic import ValidationError

from app.models.stability import RetrySummary, StabilityError


def test_stability_error_validation():
    StabilityError(
        node="diagnose",
        error_type="timeout",
        message="diagnose timed out",
        retry_attempts=2,
        degraded=True,
    )


def test_retry_summary_validation():
    summary = RetrySummary(retries={"parse": 1, "diagnose": 2})
    assert summary.retries["diagnose"] == 2


def test_invalid_error_type_rejected():
    try:
        StabilityError(
            node="parse",
            error_type="invalid",
            message="bad",
            retry_attempts=0,
            degraded=False,
        )
    except ValidationError:
        return
    raise AssertionError("Expected ValidationError")
