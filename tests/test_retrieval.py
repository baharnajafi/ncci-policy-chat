"""HybridRetriever.retrieve: fusion, code routing, reranking, the relevance gate, and graph
expansion (retrieval/hybrid.py). Uses the fake embedder and reranker from conftest."""

import pytest

from ncci_rag.retrieval.hybrid import HybridRetriever, rrf

from conftest import FakeEmbedder, FakeReranker, with_settings


def ids(result) -> list[str]:
    return [p.chunk.chunk_id for p in result.passages]


def test_rrf_rewards_agreement_and_applies_weights():
    fused = rrf({"keyword": [1, 2, 3], "vector": [2, 1, 4]})
    assert max(fused, key=lambda r: fused[r][0]) in (1, 2) and fused[2][1] == {"keyword": 2, "vector": 1}
    assert fused[3][0] < fused[1][0]
    half = rrf({"keyword": [1], "chapter": [2]}, k=60, weights={"chapter": 0.5})
    assert half[1][0] == 1 / 61 and half[2][0] == 0.5 / 61


def test_topic_question_ranks_the_matching_section_first(store, settings):
    r = HybridRetriever(store, FakeEmbedder(), settings).retrieve("Which procedures are mutually exclusive?")
    assert ids(r)[0] == "I.P.01"
    assert {"keyword", "vector"} <= set(r.passages[0].ranks)
    assert r.passed_gate and r.query_codes == [] and r.routed_chapter is None


def test_code_inside_a_stated_range_is_found_by_the_code_index(store, settings):
    r = HybridRetriever(store, FakeEmbedder(), settings).retrieve("Can CPT 64450 be reported for postoperative pain?")
    assert r.query_codes == ["64450"]
    nerve = next(p for p in r.passages if p.chunk.chunk_id == "II.B.01")
    assert nerve.ranks.get("code") == 1  # "64400-64530" contains 64450


def test_code_question_is_routed_to_the_governing_chapter(store, settings):
    r = HybridRetriever(store, FakeEmbedder(), settings).retrieve("Is diagnostic arthroscopy 29870 reported separately?")
    assert r.routed_chapter == "IV"  # Chapter IV declares CPT Codes 20000 - 29999
    assert any("chapter" in p.ranks for p in r.passages)
    assert ids(r)[0].startswith("IV.E")


def test_modifier_question_uses_the_code_index(store, settings):
    r = HybridRetriever(store, FakeEmbedder(), settings).retrieve("When is modifier XS used?")
    assert r.query_modifiers == ["XS"] and ids(r)[0] == "I.E.01" and r.passages[0].ranks.get("code") == 1


def test_chapter_filter_restricts_every_retriever(store, settings):
    r = HybridRetriever(store, FakeEmbedder(), settings).retrieve("arthroscopy modifier units", chapter="IV")
    assert ids(r) and all(i.startswith("IV.") for i in ids(r))


def test_gate_without_reranker_uses_dense_similarity(store, settings):
    retriever = HybridRetriever(store, FakeEmbedder(), settings)
    off_topic = retriever.retrieve("What is the Part B monthly premium?")
    assert not off_topic.passed_gate and off_topic.top_relevance < settings.min_dense_similarity
    assert retriever.retrieve("medically unlikely edits units of service").passed_gate


def test_reranker_sets_order_scores_and_gate(store, settings):
    retriever = HybridRetriever(store, FakeEmbedder(), settings)
    retriever.reranker = FakeReranker()
    r = retriever.retrieve("maximum units of service with imaging guidance")
    scores = [p.score for p in r.passages]
    assert scores == sorted(scores, reverse=True) and ids(r)[0] == "I.V.01"
    assert r.top_relevance == scores[0] and all("rrf" in p.ranks for p in r.passages)
    assert r.passed_gate

    strict = HybridRetriever(store, FakeEmbedder(), with_settings(settings, min_relevance=0.99))
    strict.reranker = FakeReranker()
    assert not strict.retrieve("maximum units of service with imaging guidance").passed_gate


def test_fact_passes_the_gate_and_its_linked_section_is_kept(store, settings, edit_graph):
    """A code-pair question: the PTP row is found, the gate passes even when the manual
    passages score low, and a chunk of the linked section (I.H or I.E) stays in the
    final passages even with top_k = 1 and a reranker that prefers another chunk."""
    s = with_settings(settings, top_k=1, min_dense_similarity=0.99)
    question = "Can knee arthroscopy codes 29880 and 29881 with debridement of cartilage be billed together?"
    without_graph = HybridRetriever(store, FakeEmbedder(), s).retrieve(question)
    assert ids(without_graph) == ["IV.E.02"]  # the best manual match alone is the arthroscopy text
    retriever = HybridRetriever(store, FakeEmbedder(), s, edit_graph)
    retriever.reranker = FakeReranker()  # scores the arthroscopy chunk highest, so the swap must happen
    r = retriever.retrieve(question)
    assert [f.chunk.chunk_id for f in r.facts] == ["PTP.29880-29881"]
    assert r.passed_gate
    linked = set(r.facts[0].linked_sections)
    assert linked == {"I.H", "I.E"}
    assert len(r.passages) == 1 and f"{r.passages[0].chunk.chapter_id}.{r.passages[0].chunk.section_id}" in linked
    assert "graph" in r.passages[0].ranks


def test_no_edit_tables_means_no_facts(store, settings):
    r = HybridRetriever(store, FakeEmbedder(), settings).retrieve("Can 29880 and 29881 be billed together?")
    assert r.facts == [] and "graph" not in {k for p in r.passages for k in p.ranks}


def test_cross_encoder_scores_are_squashed_to_0_1(monkeypatch):
    """The real reranker class, with the model replaced: raw logits become 0-1 scores,
    so one threshold works for every question; scores already in 0-1 are kept."""
    import numpy as np

    import ncci_rag.retrieval.rerank as rerank_mod

    class Model:
        def __init__(self, out):
            self.out, self.pairs = out, None

        def predict(self, pairs):
            self.pairs = pairs
            return np.array(self.out)

    logits = Model([3.0, -3.0])
    monkeypatch.setattr(rerank_mod, "_load", lambda name: logits)
    scores = rerank_mod.CrossEncoderReranker("bge").score("q", ["good", "bad"])
    assert logits.pairs == [("q", "good"), ("q", "bad")]
    assert 0.95 < scores[0] < 1 and 0 < scores[1] < 0.05
    monkeypatch.setattr(rerank_mod, "_load", lambda name: Model([0.2, 0.7]))
    assert rerank_mod.CrossEncoderReranker("bge").score("q", ["a", "b"]) == pytest.approx([0.2, 0.7])
    assert rerank_mod.CrossEncoderReranker("bge").score("q", []) == []
