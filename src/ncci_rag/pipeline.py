"""End-to-end entry points: build the index, and answer a question."""

from __future__ import annotations

import hashlib
import time
from pathlib import Path

from .config import Settings, get_settings
from .edits.graph import EditGraph
from .generation.answer import generate_answer
from .index.embedder import OpenAIEmbedder
from .index.store import IndexStore
from .ingest.chunker import chunk_sections
from .ingest.pdf_parser import parse_manual
from .llm_client import get_client
from .models import Answer, ScoredChunk
from .retrieval.hybrid import HybridRetriever, RetrievalResult


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_index(settings: Settings | None = None, log=print) -> IndexStore:
    s = settings or get_settings()
    if not s.pdf_path.exists():
        raise FileNotFoundError(f"PDF not found at {s.pdf_path}. See README for the download link.")
    t0 = time.time()
    sections = parse_manual(s.pdf_path)
    chunks = chunk_sections(sections)
    log(f"Parsed {len(sections)} sections into {len(chunks)} chunks ({time.time() - t0:.1f}s)")

    embedder = OpenAIEmbedder(s.embed_model, cache_path=s.cache_path)
    # Embed the chunk with its chapter/section header ("contextual chunk"), so a passage
    # about "Modifier 25" is also findable as part of "Chapter I, Section E".
    vectors = embedder.embed([f"{c.context_header}\n\n{c.text}" for c in chunks])
    log(f"Embedded {len(chunks)} chunks with {s.embed_model} ({time.time() - t0:.1f}s)")

    meta = {
        "pdf_sha256": _sha256(s.pdf_path),
        "embed_model": s.embed_model,
        "embed_dim": int(vectors.shape[1]),
        "n_chunks": len(chunks),
        "built_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    embedder.close()
    store = IndexStore.build(s.db_path, chunks, vectors, meta)
    log(f"Index written to {s.db_path}")
    return store


class QAPipeline:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        if not self.settings.db_path.exists():
            raise FileNotFoundError(f"No index at {self.settings.db_path}. Run: python -m ncci_rag ingest")
        self.store = IndexStore(self.settings.db_path)
        meta = self.store.meta()
        if meta.get("embed_model") != self.settings.embed_model:
            self.store.close()
            raise RuntimeError(
                f"Index was built with {meta.get('embed_model')} but NCCI_EMBED_MODEL is "
                f"{self.settings.embed_model}. Query and passage vectors must come from the same model; re-run ingest."
            )
        self.embedder = OpenAIEmbedder(self.settings.embed_model, cache_path=self.settings.cache_path)
        # The CMS edit tables are optional: without them, answers come from the manual alone.
        self.edits = EditGraph(self.settings.edits_db) if self.settings.edits_db.exists() else None
        self.retriever = HybridRetriever(self.store, self.embedder, self.settings, self.edits)

    def close(self) -> None:
        for part in (self.store, self.edits, self.embedder):
            if part is not None and hasattr(part, "close"):
                part.close()

    def retrieve(self, question: str, chapter: str | None = None) -> RetrievalResult:
        return self.retriever.retrieve(question, chapter)

    def ask(self, question: str, chapter: str | None = None) -> tuple[Answer, RetrievalResult]:
        result = self.retrieve(question, chapter)
        if not result.passed_gate:
            # Deterministic "not in the manual": no model call on irrelevant context.
            answer = Answer(
                question, False, [], [], result.passages,
                reason="I couldn't find this in the 2026 Medicare NCCI Policy Manual. "
                "Try rephrasing, or name the code, modifier, or chapter you mean.",
            )
            return answer, result
        facts = [ScoredChunk(f.chunk, 1.0, {"graph": i}) for i, f in enumerate(result.facts, start=1)]
        answer = generate_answer(question, facts + result.passages, self.settings.chat_model, get_client())
        return answer, result
