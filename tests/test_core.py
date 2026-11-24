"""Offline tests: no API key or network needed (models are faked)."""

from __future__ import annotations

import numpy as np
import pytest

from ncci_rag.generation.answer import format_sources, parse_and_validate, quote_found, unanchored_codes
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
    text = "CPT codes 64400-64530, J1234, 0042T and 99213; 0001A, 0002M; P.L. 101-239, revised 1/1/2026"
    assert find_codes(text) == ["64400", "J1234", "0042T", "99213", "0001A", "0002M"]
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
    passages = [ScoredChunk(_chunk("I.E.01", "Modifier 59 marks a distinct service."), 0.9),
                ScoredChunk(_chunk("I.E.02", "XS means a separate structure."), 0.8)]
    _, by_id = format_sources(passages)
    raw = {
        "answerable": True,
        "sentences": [
            {"text": "Modifier 59 marks a distinct service.", "source_ids": ["S1", "S9"],  # S9 invented
             "quotes": ["Modifier 59 marks a distinct service"]},
            {"text": "This claim has no support.", "source_ids": ["S7"], "quotes": ["x"]},  # dropped
            {"text": "XS means a separate structure.", "source_ids": ["S2"], "quotes": ["XS means a separate structure."]},
        ],
        "reason": "",
    }
    ans = parse_and_validate("q", raw, by_id, passages)
    assert ans.answerable
    assert [s.source_ids for s in ans.sentences] == [["S1"], ["S2"]]
    assert [c.source_id for c in ans.citations] == ["S1", "S2"]
    assert "[1]" in ans.text and "[2]" in ans.text and "no support" not in ans.text
    assert [r.reason for r in ans.rejected] == ["no valid source"]


def test_no_valid_support_means_no_answer():
    passages = [ScoredChunk(_chunk("I.E.01", "text"), 0.9)]
    _, by_id = format_sources(passages)
    ans = parse_and_validate("q", {"answerable": True, "sentences": [{"text": "x", "source_ids": ["S5"], "quotes": ["text"]}], "reason": ""}, by_id, passages)
    assert not ans.answerable and ans.citations == []


# ---------------------------------------------------------------- claim check
def test_quote_must_appear_in_the_cited_source():
    assert quote_found("the “separate procedure”  designation", ["The \"separate procedure\" designation means..."])
    assert quote_found("CPT codes 64400–64530 describe ... a single unit of service", ["CPT codes 64400-64530 describe injection. It is a single unit of service."])
    assert not quote_found("modifier 59 is always required", ["Modifier 59 is used only when appropriate."])
    passages = [ScoredChunk(_chunk("I.E.01", "Modifier 25 may be appended to the E&M service."), 0.9),
                ScoredChunk(_chunk("I.E.02", "Modifier 59 is never used with E&M services."), 0.9)]
    _, by_id = format_sources(passages)
    raw = {"answerable": True, "reason": "", "sentences": [
        # quote is real, but in S2, not in the cited S1
        {"text": "Modifier 59 is not used with E&M.", "source_ids": ["S1"], "quotes": ["Modifier 59 is never used with E&M services"]},
        {"text": "Modifier 25 may be appended.", "source_ids": ["S1"], "quotes": []},  # no quote
    ]}
    ans = parse_and_validate("q", raw, by_id, passages)
    assert not ans.answerable
    assert ans.rejected[0].reason.startswith("quote not found") and ans.rejected[1].reason == "no supporting quote"


def test_code_must_be_anchored_in_its_quote():
    """The real failure this check was written for: a value stated for trichiasis codes
    67820-67835 was attributed to 64450, which is named elsewhere in the same chunk."""
    text = ("7. The unit of service for procedures to correct trichiasis (e.g., CPT codes 67820-67835) is the eye. "
            "The MUEs for these codes are one.\n\n8. CPT codes 64400-64530 describe injection of anesthetic agent. "
            "All injections into the nerve constitute a single unit of service.\n\n"
            "Only one unit of service of CPT code 64450 may be reported.")
    passages = [ScoredChunk(_chunk("VIII.H.04", text, "VIII", "H"), 0.8)]
    _, by_id = format_sources(passages)
    raw = {"answerable": True, "reason": "", "sentences": [
        {"text": "The MUE value for CPT 64450 is one.", "source_ids": ["S1"], "quotes": ["The MUEs for these codes are one."]},
        {"text": "CPT 64460 describes injection of anesthetic agent.", "source_ids": ["S1"],
         "quotes": ["CPT codes 64400-64530 describe injection of anesthetic agent"]},  # covered by the range
        {"text": "Only one unit of CPT 64450 may be reported.", "source_ids": ["S1"],
         "quotes": ["Only one unit of service of CPT code 64450 may be reported"]},
        # the quote has no code, but its paragraph states the range 64400-64530
        {"text": "All injections into the nerve are one unit of service for CPT 64450.", "source_ids": ["S1"],
         "quotes": ["All injections into the nerve constitute a single unit of service"]},
    ]}
    ans = parse_and_validate("q", raw, by_id, passages)
    assert [s.text for s in ans.sentences] == ["CPT 64460 describes injection of anesthetic agent.",
                                               "Only one unit of CPT 64450 may be reported.",
                                               "All injections into the nerve are one unit of service for CPT 64450."]
    assert [r.reason for r in ans.rejected] == ["code 64450 not in the quoted paragraph"]
    assert unanchored_codes("Report 29881 and 29880 together.", ["29880 ... 29881"]) == []


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

    # Graph links: each PTP rationale must point at the Chapter I section with that topic.
    from ncci_rag.edits.graph import MODIFIER_SECTION, MUE_SECTION, RATIONALE_SECTIONS

    titles = {f"{s.chapter_id}.{s.section_id}": s.section_title.lower() for s in sections}
    assert "modifier" in titles[MODIFIER_SECTION] and "medically unlikely" in titles[MUE_SECTION]
    for rationale, sec in RATIONALE_SECTIONS.items():
        words = [w for w in rationale.replace("/", " ").split() if len(w) > 5 and w not in {"manual", "column"}]
        assert any(w in titles[sec] for w in words), (rationale, sec, titles[sec])


# ---------------------------------------------------------------- edit tables (graph)
def _edit_zips(tmp_path):
    """Tiny files in the CMS layouts: tab-separated PTP TXT and MUE CSV, each zipped."""
    import zipfile

    ptp = (
        "CPT only copyright 2025 American Medical Association.\t\t\t\t\t\t\r\n"
        "Column 1\tColumn 2\t*=in existence\tEffective\tDeletion\tModifier\tPTP Edit Rationale\r\n"
        "29880\t29881\t\t19960101\t*\t1\tHCPCS/CPT procedure code definition\r\n"
        "0001A\t0591T\t\t20220101\t20231231\t1\tCPT Manual or CMS manual coding instruction\r\n"
        "29880\t20610\t\t20000101\t*\t1\tMutually exclusive procedures\r\n"
    )
    mue = 'copyright text,,,\r\n"HCPCS/\r\nCPT Code",MUE Values,MUE Adjudication Indicator,MUE Rationale\r\n64450,10,3 Date of Service Edit: Clinical,Clinical: Data\r\n'
    with zipfile.ZipFile(tmp_path / "ptp-f1.zip", "w") as z:
        z.writestr("ccipra-v323r0-f1.TXT", ptp)
    with zipfile.ZipFile(tmp_path / "mue.zip", "w") as z:
        z.writestr("MCR_MUE_PractitionerServices_Eff_10-01-2026.csv", mue)
    return tmp_path


def test_edit_loader_and_lookups(tmp_path):
    from ncci_rag.edits.graph import EditGraph
    from ncci_rag.edits.loader import load_edits

    db = load_edits(_edit_zips(tmp_path), tmp_path / "edits.sqlite", log=lambda *_: None)
    g = EditGraph(db)
    assert g.version == "v323r0" and g.mue_effective == 20261001

    active = g.pair_fact("29881", "29880", 20261001)  # either order finds the edit
    assert active.chunk.chunk_id == "PTP.29880-29881" and active.chunk.is_fact
    assert "Column One code 29880" in active.chunk.text and "Modifier indicator 1" in active.chunk.text
    assert active.linked_sections == ["I.H", "I.E"]  # rationale section, then modifier indicators

    deleted = g.pair_fact("0001A", "0591T", 20261001)
    assert "not active on 2026-10-01" in deleted.chunk.text
    assert "active on 2023-06-01" in g.pair_fact("0001A", "0591T", 20230601).chunk.text  # date of service matters

    none = g.pair_fact("93000", "99214", 20261001)
    assert "contains no edit between codes 93000 and 99214" in none.chunk.text

    mue = g.mue_fact("64450")
    assert "MUE value of 10" in mue.chunk.text and mue.linked_sections == ["I.V"]
    assert "no MUE value" in g.mue_fact("97110").chunk.text

    summary = g.neighbour_fact("29880", 20261001)
    assert "Column One code in 2 edits" in summary.chunk.text and "20610" in summary.chunk.text

    ids = lambda q, codes: [f.chunk.chunk_id for f in g.lookup(q, codes)]  # noqa: E731
    assert ids("Can 29880 and 29881 be billed together?", ["29880", "29881"]) == ["PTP.29880-29881"]
    assert ids("What is the MUE for 64450?", ["64450"]) == ["MUE.64450"]
    assert ids("Which codes are bundled into 29880?", ["29880"]) == ["PTP.29880.summary"]
    assert ids("What does 64450 describe?", ["64450"]) == []  # no edit or MUE intent


def test_facts_are_labelled_f_and_pass_the_claim_check(tmp_path):
    from ncci_rag.edits.graph import EditGraph
    from ncci_rag.edits.loader import load_edits

    g = EditGraph(load_edits(_edit_zips(tmp_path), tmp_path / "edits.sqlite", log=lambda *_: None))
    fact = ScoredChunk(g.mue_fact("64450").chunk, 1.0)
    manual = ScoredChunk(_chunk("I.V.01", "An MUE is the maximum units of service for a code."), 0.9)
    text, by_id = format_sources([fact, manual])
    assert set(by_id) == {"F1", "S1"} and text.startswith("[F1] Medicare NCCI MUE table")
    raw = {"answerable": True, "not_covered": "", "reason": "", "sentences": [
        {"text": "The MUE value for 64450 is 10.", "source_ids": ["F1"], "quotes": ["code 64450 has an MUE value of 10 unit(s) of service"]},
        {"text": "The MUE value for 64450 is 1.", "source_ids": ["S1"], "quotes": ["An MUE is the maximum units of service"]},
    ]}
    ans = parse_and_validate("q", raw, by_id, [fact, manual])
    assert [s.text for s in ans.sentences] == ["The MUE value for 64450 is 10."]
    assert ans.citations[0].chunk.heading.startswith("Medicare NCCI MUE table") and ans.citations[0].chunk.pages == "MUE 64450"
