"""Hybrid retrieval: keyword (BM25) + vector + code index, fused with Reciprocal Rank
Fusion, then reranked by a cross-encoder.

Why three retrievers:
* BM25 is strong on exact vocabulary: "modifier 59", "MUE", "add-on code", "XS".
* Vectors are strong on paraphrase: "billing two procedures on the same day" vs.
  the manual's "reported together".
* The code index is exact on identifiers: "64450", "J1234", "0042T". It also routes a
  code to the chapter that governs it (Chapter IV covers 20000-29999), because that
  chapter's general rules apply even where the code is not named.

Why RRF: the three retrievers produce scores on different scales (BM25, cosine,
mention counts). RRF ignores the scales and fuses ranks: score = sum of 1/(k + rank).
It needs no tuning beyond k (60 is the usual default) and is robust when one
retriever returns nothing.

Graph lookup (optional, when the CMS edit tables are loaded): codes in the question
are looked up in the PTP/MUE tables. The rows found become **facts** that are passed
to the model next to the manual passages. Each fact links to the manual sections that
explain it (edit rationale -> Chapter I section, modifier indicator -> I.E, MUE -> I.V);
those sections form a fifth ranked list ("graph"), and at least one of their chunks is
kept in the final passages, so the answer can say both what applies and why.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..config import Settings
from ..edits.graph import EditGraph, Fact
from ..index.embedder import Embedder
from ..index.store import IndexStore
from ..ingest.codes import chapter_for_code, find_codes, find_modifiers
from ..models import ScoredChunk
from .rerank import CrossEncoderReranker


def rrf(ranked_lists: dict[str, list[int]], k: int = 60, weights: dict[str, float] | None = None) -> dict[int, tuple[float, dict[str, int]]]:
    """Reciprocal Rank Fusion. Returns {rowid: (score, {retriever: rank})}."""
    weights = weights or {}
    fused: dict[int, list] = {}
    for name, ids in ranked_lists.items():
        w = weights.get(name, 1.0)
        for rank, rowid in enumerate(ids, start=1):
            entry = fused.setdefault(rowid, [0.0, {}])
            entry[0] += w / (k + rank)
            entry[1][name] = rank
    return {r: (s, ranks) for r, (s, ranks) in fused.items()}


@dataclass
class RetrievalResult:
    passages: list[ScoredChunk]  # final top-k, best first
    top_relevance: float  # score used by the gate (reranker, or dense cosine if no reranker)
    passed_gate: bool
    query_codes: list[str]
    query_modifiers: list[str]
    routed_chapter: str | None
    facts: list[Fact] = field(default_factory=list)  # rows from the CMS edit tables


class HybridRetriever:
    def __init__(self, store: IndexStore, embedder: Embedder, settings: Settings, edits: EditGraph | None = None):
        self.store = store
        self.edits = edits
        self.embedder = embedder
        self.settings = settings
        self.reranker = CrossEncoderReranker(settings.reranker_model) if settings.use_reranker else None
        self._chapter_ranges = store.chapter_ranges()

    def retrieve(self, question: str, chapter: str | None = None) -> RetrievalResult:
        s = self.settings
        n = s.candidates_per_retriever
        codes, modifiers = find_codes(question), find_modifiers(question)

        qvec = self.embedder.embed([question])[0]
        dense = self.store.vector_search(qvec, n, chapter)
        lists: dict[str, list[int]] = {
            "keyword": self.store.keyword_search(question, n, chapter),
            "vector": [r for r, _ in dense],
        }
        if codes or modifiers:
            lists["code"] = self.store.code_search(codes, modifiers, n)

        # Route a code question to the chapter that governs the code, as a soft boost.
        routed = None
        if codes and not chapter:
            routed = chapter_for_code(codes[0], self._chapter_ranges)
            if routed:
                lists["chapter"] = [r for r, _ in self.store.vector_search(qvec, n, routed)]

        # Graph lookup: exact facts for the asked-about codes, plus the manual sections
        # that explain them (one hop: edit -> rationale -> section).
        facts = self.edits.lookup(question, codes) if self.edits and codes else []
        linked = {sec for f in facts for sec in f.linked_sections}
        if linked:
            lists["graph"] = self.store.section_search(qvec, linked, n)

        fused = rrf(lists, k=s.rrf_k, weights={"chapter": 0.5})
        chunks = self.store.chunks()
        pool = sorted(fused.items(), key=lambda kv: -kv[1][0])[: s.rerank_pool]
        candidates = [ScoredChunk(chunks[r], score, ranks) for r, (score, ranks) in pool]

        if self.reranker and candidates:
            scores = self.reranker.score(
                question, [f"{c.chunk.context_header}\n{c.chunk.text}" for c in candidates]
            )
            for rrf_rank, (c, sc) in enumerate(zip(candidates, scores), start=1):
                c.ranks["rrf"] = rrf_rank
                c.score = sc
            candidates.sort(key=lambda c: -c.score)
            top = candidates[0].score if candidates else 0.0
            passed = top >= s.min_relevance
        else:
            top = dense[0][1] if dense else 0.0
            passed = top >= s.min_dense_similarity

        top_k = candidates[: s.top_k]
        if linked and not any(_section(c) in linked for c in top_k):
            best_linked = next((c for c in candidates if _section(c) in linked), None)
            if best_linked is not None:
                top_k = top_k[: s.top_k - 1] + [best_linked]  # keep the "why" for the fact
        if facts:
            passed = True  # an exact table row is relevant evidence by construction

        return RetrievalResult(
            passages=top_k,
            top_relevance=top,
            passed_gate=passed,
            query_codes=codes,
            query_modifiers=modifiers,
            routed_chapter=routed,
            facts=facts,
        )


def _section(c: ScoredChunk) -> str:
    return f"{c.chunk.chapter_id}.{c.chunk.section_id}"
