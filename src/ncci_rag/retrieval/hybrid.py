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
"""

from __future__ import annotations

from dataclasses import dataclass

from ..config import Settings
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


class HybridRetriever:
    def __init__(self, store: IndexStore, embedder: Embedder, settings: Settings):
        self.store = store
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

        return RetrievalResult(
            passages=candidates[: s.top_k],
            top_relevance=top,
            passed_gate=passed,
            query_codes=codes,
            query_modifiers=modifiers,
            routed_chapter=routed,
        )
