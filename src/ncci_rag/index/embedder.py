"""Embeddings with batching, retries, and a persistent cache.

The cache is keyed by (model, text), so re-running ingestion after a parser or
chunking change only pays for chunks whose text actually changed.
"""

from __future__ import annotations

import hashlib
import sqlite3
import time
from pathlib import Path
from typing import Protocol

import numpy as np


class Embedder(Protocol):
    model: str

    def embed(self, texts: list[str]) -> np.ndarray:  # (n, dim), L2-normalised float32
        ...

    def close(self) -> None: ...


def _normalise(m: np.ndarray) -> np.ndarray:
    m = m.astype(np.float32)
    norms = np.linalg.norm(m, axis=1, keepdims=True)
    return m / np.clip(norms, 1e-12, None)


class OpenAIEmbedder:
    def __init__(self, model: str, cache_path: Path | None = None, batch_size: int = 64, max_retries: int = 5):
        self.model = model
        self.batch_size = batch_size
        self.max_retries = max_retries
        self._cache = None
        if cache_path:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            self._cache = sqlite3.connect(cache_path)
            self._cache.execute("CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, vec BLOB, dim INTEGER)")

    def close(self) -> None:
        if self._cache is not None:
            self._cache.close()

    def _key(self, text: str) -> str:
        return hashlib.sha256(f"{self.model}\n{text}".encode()).hexdigest()

    def _call(self, batch: list[str]) -> list[list[float]]:
        from openai import APIConnectionError, APIStatusError, RateLimitError

        from ..llm_client import get_client

        delay = 2.0
        for attempt in range(self.max_retries):
            try:
                resp = get_client().embeddings.create(model=self.model, input=batch)
                return [d.embedding for d in resp.data]
            except (RateLimitError, APIConnectionError):  # transient: back off and retry
                if attempt == self.max_retries - 1:
                    raise
                time.sleep(delay)
                delay *= 2
            except APIStatusError as e:
                if e.status_code >= 500 and attempt < self.max_retries - 1:
                    time.sleep(delay)
                    delay *= 2
                    continue
                raise
        raise RuntimeError("unreachable")

    def embed(self, texts: list[str]) -> np.ndarray:
        vectors: list[np.ndarray | None] = [None] * len(texts)
        todo: list[int] = []
        for i, t in enumerate(texts):
            row = None
            if self._cache is not None:
                row = self._cache.execute("SELECT vec FROM cache WHERE key = ?", (self._key(t),)).fetchone()
            if row:
                vectors[i] = np.frombuffer(row[0], dtype=np.float32)
            else:
                todo.append(i)

        for start in range(0, len(todo), self.batch_size):
            idx = todo[start : start + self.batch_size]
            embs = self._call([texts[i] for i in idx])
            for i, e in zip(idx, embs, strict=True):
                v = np.asarray(e, dtype=np.float32)
                vectors[i] = v
                if self._cache is not None:
                    self._cache.execute(
                        "INSERT OR REPLACE INTO cache VALUES (?, ?, ?)", (self._key(texts[i]), v.tobytes(), len(v))
                    )
            if self._cache is not None:
                self._cache.commit()

        return _normalise(np.vstack(vectors))
