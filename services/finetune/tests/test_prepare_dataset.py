"""Tests for dataset preparation utilities."""

import pytest

from app.data.prepare import prepare_sample


class TestPrepareSampleMissingLabel:
    """prepare_sample must reject samples that have no label."""

    def test_raises_value_error_when_label_key_missing(self):
        """A sample dict without a 'label' key should raise ValueError."""
        sample = {"text": "build failed: OOM killed"}
        with pytest.raises(ValueError, match="label"):
            _ = prepare_sample(sample)

    def test_raises_value_error_when_label_is_none(self):
        """A sample dict where label is None should raise ValueError."""
        sample = {"text": "build failed: OOM killed", "label": None}
        with pytest.raises(ValueError, match="label"):
            _ = prepare_sample(sample)

    def test_raises_value_error_when_label_is_empty_string(self):
        """A sample dict where label is an empty string should raise ValueError."""
        sample = {"text": "build failed: OOM killed", "label": ""}
        with pytest.raises(ValueError, match="label"):
            _ = prepare_sample(sample)


class TestPrepareSampleSuccess:
    """prepare_sample should return formatted data when label is present."""

    def test_returns_dict_with_valid_sample(self):
        """A sample with text and label should return a formatted dict."""
        sample = {"text": "build failed: OOM killed", "label": "oom"}
        result = prepare_sample(sample)
        assert isinstance(result, dict)
        assert result["label"] == "oom"
        assert result["text"] == "build failed: OOM killed"
