"""Tests for secondary rerank configuration in agent-orchestrator."""

from app.config import Settings


class TestSecondaryRerankConfig:
    """Verify secondary_rerank_enabled and secondary_rerank_targets defaults."""

    def test_secondary_rerank_enabled_defaults_to_false(self, monkeypatch):
        """secondary_rerank_enabled should default to False."""
        monkeypatch.delenv("SECONDARY_RERANK_ENABLED", raising=False)
        s = Settings(_env_file=None, openai_api_key="test")  # pyright: ignore[reportCallIssue]
        assert s.secondary_rerank_enabled is False

    def test_secondary_rerank_targets_defaults_to_empty_list(self, monkeypatch):
        """secondary_rerank_targets should default to empty list."""
        monkeypatch.delenv("SECONDARY_RERANK_TARGETS", raising=False)
        s = Settings(_env_file=None, openai_api_key="test")  # pyright: ignore[reportCallIssue]
        assert s.secondary_rerank_targets == []

    def test_secondary_rerank_enabled_respects_env(self, monkeypatch):
        """Setting SECONDARY_RERANK_ENABLED=true via env should enable it."""
        monkeypatch.setenv("SECONDARY_RERANK_ENABLED", "true")
        s = Settings(_env_file=None, openai_api_key="test")  # pyright: ignore[reportCallIssue]
        assert s.secondary_rerank_enabled is True

    def test_secondary_rerank_targets_from_env(self, monkeypatch):
        """Setting SECONDARY_RERANK_TARGETS via env as JSON list."""
        monkeypatch.setenv("SECONDARY_RERANK_TARGETS", '["build_failure_triage","code_review"]')
        s = Settings(_env_file=None, openai_api_key="test")  # pyright: ignore[reportCallIssue]
        assert s.secondary_rerank_targets == ["build_failure_triage", "code_review"]
