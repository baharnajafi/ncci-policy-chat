"""First-run setup for a hosted app (Streamlit Community Cloud, Hugging Face Spaces).

A hosted app starts from the Git repository alone: no PDF, no index, and the API key
in the platform's secret store instead of a .env file. On its first start the app:

1. copies known secrets into environment variables, where config.py reads them;
2. downloads the public manual PDF from CMS if it is missing;
3. builds the index if it is missing or was built with a different embedding model
   (about 30 seconds and a few cents of embeddings; later restarts reuse it while the
   container's disk lives).

The CMS edit tables are deliberately not fetched: their AMA CPT license allows
internal use only, so a public deployment answers from the manual alone.

Access control is minimal on purpose: an optional shared password and a per-session
question limit, both to keep a public link from spending the API key freely.
"""

from __future__ import annotations

import hmac
import os
import urllib.request
from collections.abc import Callable, Mapping
from pathlib import Path

from .config import Settings

MANUAL_URL = "https://www.cms.gov/files/document/2026-ncci-medicare-policy-manual-all-chapters.pdf"

# Secrets copied into the environment. Anything else in the secret store is ignored.
SECRET_KEYS = (
    "OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY", "AZURE_OPENAI_API_VERSION",
    "APP_PASSWORD", "NCCI_EMBED_MODEL", "NCCI_CHAT_MODEL", "NCCI_RERANKER", "NCCI_MIN_RELEVANCE",
    "NCCI_MIN_DENSE_SIM", "NCCI_TOP_K", "NCCI_MAX_QUESTIONS", "NCCI_PDF_URL",
)


def apply_secrets(secrets: Mapping) -> list[str]:
    """Copy known secrets into os.environ (without overriding variables already set).
    Returns the names applied, never the values."""
    applied = []
    for key in SECRET_KEYS:
        if key in secrets and key not in os.environ and str(secrets[key]).strip():
            os.environ[key] = str(secrets[key]).strip()
            applied.append(key)
    return applied


def download(url: str, dest: Path, timeout: int = 60) -> None:
    """Download to a temporary file and rename, so a failed download leaves nothing behind."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    req = urllib.request.Request(url, headers={"User-Agent": "ncci-policy-chat"})
    with urllib.request.urlopen(req, timeout=timeout) as resp, open(tmp, "wb") as fh:
        fh.write(resp.read())
    if tmp.read_bytes()[:5] != b"%PDF-":
        tmp.unlink(missing_ok=True)
        raise RuntimeError(f"{url} did not return a PDF. Download the manual manually into {dest} (see README).")
    tmp.replace(dest)


def index_is_current(settings: Settings) -> bool:
    if not settings.db_path.exists():
        return False
    from .index.store import IndexStore

    store = IndexStore(settings.db_path)
    try:
        return store.meta().get("embed_model") == settings.embed_model
    finally:
        store.close()


def ensure_ready(settings: Settings, log: Callable[[str], None] = print,
                 fetch: Callable[[str, Path], None] = download) -> str:
    """Make sure the PDF and a current index exist. Returns "ready" or "built"."""
    if index_is_current(settings):
        return "ready"
    if not settings.pdf_path.exists():
        url = os.getenv("NCCI_PDF_URL", MANUAL_URL)
        log(f"Downloading the manual from {url}")
        settings.pdf_path.parent.mkdir(parents=True, exist_ok=True)
        fetch(url, settings.pdf_path)
    from .pipeline import build_index

    build_index(settings, log=log).close()
    return "built"


def password_ok(given: str | None, expected: str | None) -> bool:
    """No password configured -> open. Otherwise a constant-time comparison."""
    if not expected:
        return True
    return bool(given) and hmac.compare_digest(given.encode(), expected.encode())


def questions_left(asked: int, limit: int) -> int | None:
    """Remaining questions in this session, or None when unlimited."""
    return None if limit <= 0 else max(limit - asked, 0)
