"""The index: one SQLite file holding chunks, a keyword index, vectors, and a code index.

Why SQLite and not a vector database: the manual yields ~650 chunks. Exact cosine
similarity over 650 vectors takes well under a millisecond with numpy, so an
approximate-nearest-neighbour index (HNSW) would add a dependency and a recall/latency
trade-off with no benefit at this size. SQLite gives us BM25 through its built-in FTS5
extension, transactions, and a single file that ships with the repo instructions.
At larger scale (many manuals, many tenants), the same interfaces would sit on
Azure AI Search, OpenSearch, or pgvector (see docs/DESIGN.md).
"""

from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path

import numpy as np

from ..ingest.codes import find_ranges, in_range
from ..models import Chunk

SCHEMA = """
CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE chunks (
    rowid INTEGER PRIMARY KEY,
    chunk_id TEXT UNIQUE, chapter_id TEXT, chapter_title TEXT, code_range TEXT,
    section_id TEXT, section_title TEXT,
    page_start INTEGER, page_end INTEGER, label_start TEXT, label_end TEXT,
    text TEXT, codes TEXT, modifiers TEXT
);
-- Keyword index over the chunk text plus its chapter/section header.
-- porter stemming: "modifiers" matches "modifier", "reported" matches "report".
CREATE VIRTUAL TABLE chunks_fts USING fts5(header, body, tokenize = "porter unicode61");
CREATE TABLE vectors (rowid INTEGER PRIMARY KEY, vec BLOB);
-- Code index: which chunks mention which code or modifier, and which code ranges.
CREATE TABLE code_mentions (code TEXT, kind TEXT, rowid INTEGER);
CREATE INDEX code_mentions_code ON code_mentions(code);
CREATE TABLE code_ranges (start TEXT, end TEXT, rowid INTEGER);
"""

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "can", "do", "does", "for", "from", "how", "i", "if",
    "in", "is", "it", "its", "may", "of", "on", "or", "should", "that", "the", "their", "this", "to", "was",
    "what", "when", "where", "which", "who", "why", "will", "with", "you", "your",
}


def fts_query(text: str) -> str:
    """Build a safe FTS5 query: quoted terms joined with OR (BM25 still rewards
    chunks matching more terms). Quoting stops user input being read as FTS syntax."""
    terms = [t for t in re.findall(r"[A-Za-z0-9]+", text) if t.lower() not in STOPWORDS]
    return " OR ".join(f'"{t}"' for t in dict.fromkeys(terms))


class IndexStore:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self._matrix: np.ndarray | None = None
        self._rowids: np.ndarray | None = None
        self._chunks: dict[int, Chunk] | None = None

    # ------------------------------------------------------------------ build
    @classmethod
    def build(cls, path: Path, chunks: list[Chunk], vectors: np.ndarray, meta: dict) -> IndexStore:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".building")
        tmp.unlink(missing_ok=True)
        conn = sqlite3.connect(tmp)
        conn.executescript(SCHEMA)
        with conn:
            for rowid, (c, v) in enumerate(zip(chunks, vectors, strict=True), start=1):
                conn.execute(
                    "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (rowid, c.chunk_id, c.chapter_id, c.chapter_title, c.code_range, c.section_id,
                     c.section_title, c.page_start, c.page_end, c.label_start, c.label_end, c.text,
                     json.dumps(c.codes), json.dumps(c.modifiers)),
                )
                conn.execute("INSERT INTO chunks_fts(rowid, header, body) VALUES (?,?,?)", (rowid, c.context_header, c.text))
                conn.execute("INSERT INTO vectors VALUES (?, ?)", (rowid, np.asarray(v, dtype=np.float32).tobytes()))
                for code in c.codes:
                    conn.execute("INSERT INTO code_mentions VALUES (?, 'code', ?)", (code, rowid))
                for mod in c.modifiers:
                    conn.execute("INSERT INTO code_mentions VALUES (?, 'modifier', ?)", (mod, rowid))
                for start, end in find_ranges(c.text):
                    conn.execute("INSERT INTO code_ranges VALUES (?, ?, ?)", (start, end, rowid))
            for k, v in meta.items():
                conn.execute("INSERT INTO meta VALUES (?, ?)", (k, json.dumps(v)))
        conn.close()
        tmp.replace(path)  # atomic swap: a failed build never leaves a half-written index
        return cls(path)

    def close(self) -> None:
        self.conn.close()

    # ------------------------------------------------------------------ read
    def meta(self) -> dict:
        return {k: json.loads(v) for k, v in self.conn.execute("SELECT key, value FROM meta")}

    def chunks(self) -> dict[int, Chunk]:
        if self._chunks is None:
            self._chunks = {}
            for row in self.conn.execute("SELECT * FROM chunks"):
                (rowid, chunk_id, chapter_id, chapter_title, code_range, section_id, section_title,
                 page_start, page_end, label_start, label_end, text, codes, modifiers) = row
                self._chunks[rowid] = Chunk(chunk_id, chapter_id, chapter_title, code_range, section_id,
                                            section_title, page_start, page_end, label_start, label_end,
                                            text, json.loads(codes), json.loads(modifiers))
        return self._chunks

    def _load_vectors(self) -> None:
        rows = self.conn.execute("SELECT rowid, vec FROM vectors ORDER BY rowid").fetchall()
        self._rowids = np.array([r[0] for r in rows])
        self._matrix = np.vstack([np.frombuffer(r[1], dtype=np.float32) for r in rows])

    def chapter_ranges(self) -> dict[str, tuple[str, str]]:
        """Chapter -> (first code, last code), from titles like "CPT Codes 20000 - 29999"."""
        out = {}
        for chapter_id, code_range in self.conn.execute(
            "SELECT DISTINCT chapter_id, code_range FROM chunks WHERE code_range IS NOT NULL"
        ):
            ranges = find_ranges(code_range)
            if ranges:
                out[chapter_id] = ranges[0]
        return out

    # ------------------------------------------------------------------ retrievers
    def keyword_search(self, query: str, k: int, chapter: str | None = None) -> list[int]:
        q = fts_query(query)
        if not q:
            return []
        sql = (
            "SELECT f.rowid FROM chunks_fts f JOIN chunks c ON c.rowid = f.rowid "
            "WHERE chunks_fts MATCH ? " + ("AND c.chapter_id = ? " if chapter else "") +
            # bm25 weights: header matches count less than body matches
            "ORDER BY bm25(chunks_fts, 0.5, 1.0) LIMIT ?"
        )
        params = (q, chapter, k) if chapter else (q, k)
        return [r[0] for r in self.conn.execute(sql, params)]

    def vector_search(self, query_vec: np.ndarray, k: int, chapter: str | None = None) -> list[tuple[int, float]]:
        if self._matrix is None:
            self._load_vectors()
        sims = self._matrix @ query_vec.astype(np.float32)
        order = np.argsort(-sims)
        chunks = self.chunks() if chapter else None
        out = []
        for i in order:
            rowid = int(self._rowids[i])
            if chapter and chunks[rowid].chapter_id != chapter:
                continue
            out.append((rowid, float(sims[i])))
            if len(out) == k:
                break
        return out

    def section_search(self, query_vec: np.ndarray, sections: set[str], k: int) -> list[int]:
        """Chunks of the given sections ("I.P"), most similar to the query first. Used for
        graph expansion: an edit's rationale points to the section that explains it."""
        if self._matrix is None:
            self._load_vectors()
        chunks = self.chunks()
        order = np.argsort(-(self._matrix @ query_vec.astype(np.float32)))
        out = []
        for i in order:
            c = chunks[int(self._rowids[i])]
            if f"{c.chapter_id}.{c.section_id}" in sections:
                out.append(int(self._rowids[i]))
                if len(out) == k:
                    break
        return out

    def code_search(self, codes: list[str], modifiers: list[str], k: int) -> list[int]:
        """Chunks that mention the asked-about codes/modifiers, most mentions first.
        A code also matches chunks that mention a range containing it (e.g. 64450 in
        "64400-64530")."""
        hits: dict[int, int] = {}
        for code in codes:
            for (rowid,) in self.conn.execute("SELECT rowid FROM code_mentions WHERE code = ? AND kind = 'code'", (code,)):
                hits[rowid] = hits.get(rowid, 0) + 2
            for start, end, rowid in self.conn.execute("SELECT start, end, rowid FROM code_ranges"):
                if in_range(code, start, end):
                    hits[rowid] = hits.get(rowid, 0) + 1
        for mod in modifiers:
            for (rowid,) in self.conn.execute(
                "SELECT rowid FROM code_mentions WHERE code = ? AND kind = 'modifier'", (mod,)
            ):
                hits[rowid] = hits.get(rowid, 0) + 2
        return [r for r, _ in sorted(hits.items(), key=lambda kv: (-kv[1], kv[0]))][:k]
