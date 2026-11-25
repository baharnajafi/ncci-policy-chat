"""Settings, read from environment variables (and a local .env file).

Everything that changes retrieval quality or cost is a setting, so experiments do not
require code changes and the eval report can record exactly what was run.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

try:  # optional: load a local .env file if python-dotenv is installed
    from dotenv import load_dotenv

    # The project's .env wins over variables inherited from the shell. Otherwise a stale
    # OPENAI_API_KEY exported in ~/.zshrc silently replaces the key the README tells you
    # to put in .env (a real 401 seen during setup). Hosted deployments have no .env, so
    # their platform secrets are unaffected.
    load_dotenv(override=True)
except ImportError:  # pragma: no cover
    pass


def _env(name: str, default: str) -> str:
    return os.getenv(name, default)


@dataclass(frozen=True)
class Settings:
    # Files
    pdf_path: Path = field(default_factory=lambda: Path(_env("NCCI_PDF", "data/2026_ncci_medicare_policy_manual_all-chapters.pdf")))
    db_path: Path = field(default_factory=lambda: Path(_env("NCCI_DB", "data/index.sqlite")))
    cache_path: Path = field(default_factory=lambda: Path(_env("NCCI_EMBED_CACHE", "data/embedding_cache.sqlite")))
    # CMS edit files (PTP pairs, MUE values): zips in edits_dir, loaded into edits_db.
    # Optional: without edits_db the app answers from the manual alone.
    edits_dir: Path = field(default_factory=lambda: Path(_env("NCCI_EDITS_DIR", "data/edits")))
    edits_db: Path = field(default_factory=lambda: Path(_env("NCCI_EDITS_DB", "data/edits.sqlite")))

    # Models (OpenAI by default; Azure OpenAI if AZURE_OPENAI_ENDPOINT is set)
    embed_model: str = field(default_factory=lambda: _env("NCCI_EMBED_MODEL", "text-embedding-3-large"))
    chat_model: str = field(default_factory=lambda: _env("NCCI_CHAT_MODEL", "gpt-4.1"))
    reranker_model: str = field(default_factory=lambda: _env("NCCI_RERANKER", "BAAI/bge-reranker-base"))  # "none" to disable

    # Retrieval. Every default is read when Settings() is created, not at import, so env
    # vars set later (e.g. from Streamlit secrets) still apply.
    candidates_per_retriever: int = field(default_factory=lambda: int(_env("NCCI_CANDIDATES", "40")))
    rerank_pool: int = field(default_factory=lambda: int(_env("NCCI_RERANK_POOL", "30")))
    top_k: int = field(default_factory=lambda: int(_env("NCCI_TOP_K", "6")))
    rrf_k: int = field(default_factory=lambda: int(_env("NCCI_RRF_K", "60")))
    # Relevance gate: below this, answer "not in the manual" without calling the LLM.
    # Calibrated with eval/run_eval.py on 20 positives and 10 off-topic negatives: no gate
    # error from 0.10 to 0.70 with bge-reranker-base (0.01 to 0.90 with MiniLM). 0.30 keeps
    # a wide margin over the highest negative (0.05) without refusing any positive (lowest
    # 0.78). Scores are not calibrated probabilities. Reranker scores are 0-1;
    # if the reranker is disabled, the gate uses the top dense cosine similarity instead.
    min_relevance: float = field(default_factory=lambda: float(_env("NCCI_MIN_RELEVANCE", "0.30")))
    min_dense_similarity: float = field(default_factory=lambda: float(_env("NCCI_MIN_DENSE_SIM", "0.30")))

    # Hosted app: questions allowed per browser session (0 = unlimited), to bound API cost.
    max_questions_per_session: int = field(default_factory=lambda: int(_env("NCCI_MAX_QUESTIONS", "0")))

    @property
    def use_reranker(self) -> bool:
        return self.reranker_model.lower() not in {"", "none", "off"}


def get_settings() -> Settings:
    return Settings()
