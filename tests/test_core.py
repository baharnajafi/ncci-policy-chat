"""Offline tests: no API key or network needed (models are faked)."""

from __future__ import annotations

import numpy as np
import pytest

from ncci_rag.generation.answer import format_sources, parse_and_validate
from ncci_rag.index.store import IndexStore, fts_query
from ncci_rag.ingest.chunker import chunk_sections
from ncci_rag.ingest.codes import chapter_for_code, find_codes, find_modifiers, find_ranges, in_range
from ncci_rag.models import Chunk, Paragraph, ScoredChunk, Section
from ncci_rag.retrieval.hybrid import rrf


# ---------------------------------------------------------------- codes
def test_modifier_lists_and_false_positives():
    assert find_modifiers("modifiers 25, 58, 59, XE, XP, XS, and XU") == ["25", "58", "59", "XE", "XP", "XS", "XU"]
    assert find_modifiers("the modifier is appended to the code") == []
    assert find_modifiers("append the 59 modifier") == ["59"]
    assert find_modifiers("modifier -59 or modifier XS") == ["59", "XS"]


def test_codes_and_ranges():
    text = "CPT codes 64400-64530, J1234, 0042T and 99213; P.L. 101-239, revised 1/1/2026"
    assert find_codes(text) == ["64400", "J1234", "0042T", "99213"]
    assert find_ranges(text) == [("64400", "64530")]
    assert in_range("64450", "64400", "64530")
    assert not in_range("0042T", "00000", "01999")  # Category III is not a 5-digit CPT code


def test_chapter_routing():
    ranges = {"IV": ("20000", "29999"), "XII": ("A0000", "V9999"), "XIII": ("0001T", "0999T")}
    assert chapter_for_code("27447", ranges) == "IV"
    assert chapter_for_code("J1234", ranges) == "XII"
    assert chapter_for_code("0042T", ranges) == "XIII"
    assert chapter_for_code("99213", ranges) is None


# ---------------------------------------------------------------- chunking
def _section(sid: str, n_paras: int, words: int) -> Section:
    paras = [Paragraph(" ".join(["word"] * words), page=10 + i // 3, page_label=f"I-{3 + i // 3}") for i in range(n_paras)]
    return Section("I", "General Correct Coding Policies", None, sid, "Title", paras)


def test_chunks_never_cross_sections_and_respect_size():
    chunks = chunk_sections([_section("A", 10, 80), _section("B", 2, 40)], target_words=250, max_words=400)
    assert {c.section_id for c in chunks} == {"A", "B"}
    assert all(c.chunk_id.startswith(f"I.{c.section_id}.") for c in chunks)
    assert all(len(c.text.split()) <= 400 for c in chunks)
    assert len({c.chunk_id for c in chunks}) == len(chunks)


def test_long_paragraph_is_split_at_sentences():
    long = " ".join(f"Sentence number {i} has several words in it." for i in range(120))
    sec = Section("I", "T", None, "A", "T", [Paragraph(long, 10, "I-3")])
    chunks = chunk_sections([sec], target_words=250, max_words=300)
    assert len(chunks) >= 3 and all(len(c.text.split()) <= 300 for c in chunks)


# ---------------------------------------------------------------- retrieval
def test_fts_query_is_safe():
    q = fts_query('What is "modifier" 59 AND NOT (x)?')
    assert '"59"' in q and '"modifier"' in q and "NOT" not in q.replace('"NOT"', "")


def test_rrf_rewards_agreement():
    fused = rrf({"keyword": [1, 2, 3], "vector": [2, 1, 4]})
    best = max(fused, key=lambda r: fused[r][0])
    assert best in (1, 2) and fused[2][1] == {"keyword": 2, "vector": 1}
    assert fused[3][0] < fused[1][0]


def _chunk(cid: str, text: str, chapter="I", section="E") -> Chunk:
    return Chunk(cid, chapter, "General", None, section, "Modifiers", 30, 30, "I-14", "I-14", text,
                 find_codes(text), find_modifiers(text))


def test_store_keyword_and_code_search(tmp_path):
    chunks = [
        _chunk("I.E.01", "Modifier 59 indicates a distinct procedural service."),
        _chunk("I.V.01", "Medically Unlikely Edits limit units of service.", section="V"),
        _chunk("II.B.01", "Peripheral nerve blocks, CPT codes 64400-64530, may be reported.", chapter="II", section="B"),
    ]
    vecs = np.eye(3, dtype=np.float32)
    store = IndexStore.build(tmp_path / "i.sqlite", chunks, vecs, {"embed_model": "fake"})
    ids = {r: c.chunk_id for r, c in store.chunks().items()}
    assert ids[store.keyword_search("units of service", 3)[0]] == "I.V.01"
    assert ids[store.code_search([], ["59"], 3)[0]] == "I.E.01"
    assert ids[store.code_search(["64450"], [], 3)[0]] == "II.B.01"  # via the range 64400-64530
    assert ids[store.vector_search(np.array([0, 0, 1], dtype=np.float32), 1)[0][0]] == "II.B.01"


# ---------------------------------------------------------------- citations
def test_citations_drop_invented_sources_and_unsupported_sentences():
    passages = [ScoredChunk(_chunk("I.E.01", "Modifier 59 ..."), 0.9), ScoredChunk(_chunk("I.E.02", "XS ..."), 0.8)]
    _, by_id = format_sources(passages)
    raw = {
        "answerable": True,
        "sentences": [
            {"text": "Modifier 59 marks a distinct service.", "source_ids": ["S1", "S9"]},  # S9 invented
            {"text": "This claim has no support.", "source_ids": ["S7"]},  # dropped entirely
            {"text": "XS means a separate structure.", "source_ids": ["S2"]},
        ],
        "reason": "",
    }
    ans = parse_and_validate("q", raw, by_id, passages)
    assert ans.answerable
    assert [s.source_ids for s in ans.sentences] == [["S1"], ["S2"]]
    assert [c.source_id for c in ans.citations] == ["S1", "S2"]
    assert "[1]" in ans.text and "[2]" in ans.text and "no support" not in ans.text


def test_no_valid_support_means_no_answer():
    passages = [ScoredChunk(_chunk("I.E.01", "text"), 0.9)]
    _, by_id = format_sources(passages)
    ans = parse_and_validate("q", {"answerable": True, "sentences": [{"text": "x", "source_ids": ["S5"]}], "reason": ""}, by_id, passages)
    assert not ans.answerable and ans.citations == []


# ---------------------------------------------------------------- parser (needs the PDF)
PDF = "data/2026_ncci_medicare_policy_manual_all-chapters.pdf"


@pytest.mark.skipif(not __import__("os").path.exists(PDF), reason="manual PDF not downloaded")
def test_parser_on_real_manual():
    from ncci_rag.ingest.pdf_parser import parse_manual

    sections = parse_manual(PDF)
    keys = {f"{s.chapter_id}.{s.section_id}" for s in sections}
    assert {"I.E", "I.V", "IV.E", "IX.B", "XIII.E", "Intro.purpose"} <= keys
    ch4 = next(s for s in sections if s.chapter_id == "IV")
    assert ch4.code_range and "20000" in ch4.code_range
    mods = next(s for s in sections if s.chapter_id == "I" and s.section_id == "E")
    assert mods.paragraphs[0].page_label.startswith("I-")
