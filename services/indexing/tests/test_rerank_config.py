"""Tests for rerank configuration settings in indexing service."""

from app.config import Settings


class TestRerankConfigDefaults:
    """Verify rerank_enabled and rerank_model_name have correct defaults."""

    def test_rerank_enabled_defaults_to_true(self, monkeypatch):
        monkeypatch.delenv("RERANK_ENABLED", raising=False)
        s = Settings(_env_file=None)  # pyright: ignore[reportCallIssue]
        assert s.rerank_enabled is True

    def test_rerank_model_name_has_default(self, monkeypatch):
        monkeypatch.delenv("RERANK_MODEL_NAME", raising=False)
        s = Settings(_env_file=None)  # pyright: ignore[reportCallIssue]
        assert s.rerank_model_name == "BAAI/bge-reranker-base"

    def test_rerank_enabled_respects_env_var(self, monkeypatch):
        """Setting RERANK_ENABLED=true via env should enable reranking."""
        monkeypatch.setenv("RERANK_ENABLED", "true")
        s = Settings(_env_file=None)  # pyright: ignore[reportCallIssue]
        assert s.rerank_enabled is True

    def test_rerank_model_name_respects_env_var(self, monkeypatch):
        """Setting RERANK_MODEL_NAME via env should override the default."""
        monkeypatch.setenv("RERANK_MODEL_NAME", "cross-encoder/ms-marco-TinyBERT-L-2-v2")
        s = Settings(_env_file=None)  # pyright: ignore[reportCallIssue]
        assert s.rerank_model_name == "cross-encoder/ms-marco-TinyBERT-L-2-v2"
