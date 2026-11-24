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

    load_dotenv()
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

    # Retrieval
    candidates_per_retriever: int = int(_env("NCCI_CANDIDATES", "40"))
    rerank_pool: int = int(_env("NCCI_RERANK_POOL", "30"))
    top_k: int = int(_env("NCCI_TOP_K", "6"))
    rrf_k: int = int(_env("NCCI_RRF_K", "60"))
    # Relevance gate: below this, answer "not in the manual" without calling the LLM.
    # Calibrated with eval/run_eval.py (see README). Reranker scores are 0-1;
    # if the reranker is disabled, the gate uses the top dense cosine similarity instead.
    min_relevance: float = float(_env("NCCI_MIN_RELEVANCE", "0.10"))
    min_dense_similarity: float = float(_env("NCCI_MIN_DENSE_SIM", "0.30"))

    @property
    def use_reranker(self) -> bool:
        return self.reranker_model.lower() not in {"", "none", "off"}


def get_settings() -> Settings:
    return Settings()
