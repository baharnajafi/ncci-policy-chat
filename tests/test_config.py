"""Settings come from the environment when Settings() is created (config.py)."""

from ncci_rag.config import Settings


def test_env_is_read_at_creation_not_import(monkeypatch):
    monkeypatch.setenv("NCCI_TOP_K", "9")
    monkeypatch.setenv("NCCI_MIN_RELEVANCE", "0.42")
    monkeypatch.setenv("NCCI_RERANKER", "none")
    s = Settings()
    assert (s.top_k, s.min_relevance, s.use_reranker) == (9, 0.42, False)
    monkeypatch.delenv("NCCI_TOP_K")
    assert Settings().top_k == 6
