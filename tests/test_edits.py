"""CMS edit tables: loader, graph lookups, and facts as citable sources (edits/)."""

from ncci_rag.generation.answer import format_sources, parse_and_validate
from ncci_rag.models import ScoredChunk

from conftest import make_chunk


def test_edit_loader_and_lookups(edit_graph):
    g = edit_graph
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


def test_loader_needs_zip_files(tmp_path):
    import pytest

    from ncci_rag.edits.loader import load_edits

    with pytest.raises(FileNotFoundError):
        load_edits(tmp_path, tmp_path / "edits.sqlite", log=lambda *_: None)


def test_facts_are_labelled_f_and_pass_the_claim_check(edit_graph):
    fact = ScoredChunk(edit_graph.mue_fact("64450").chunk, 1.0)
    manual = ScoredChunk(make_chunk("I.V.01", "An MUE is the maximum units of service for a code."), 0.9)
    text, by_id = format_sources([fact, manual])
    assert set(by_id) == {"F1", "S1"} and text.startswith("[F1] Medicare NCCI MUE table")
    raw = {"answerable": True, "not_covered": "", "reason": "", "sentences": [
        {"text": "The MUE value for 64450 is 10.", "source_ids": ["F1"], "quotes": ["code 64450 has an MUE value of 10 unit(s) of service"]},
        {"text": "The MUE value for 64450 is 1.", "source_ids": ["S1"], "quotes": ["An MUE is the maximum units of service"]},
    ]}
    ans = parse_and_validate("q", raw, by_id, [fact, manual])
    assert [s.text for s in ans.sentences] == ["The MUE value for 64450 is 10."]
    assert ans.citations[0].chunk.heading.startswith("Medicare NCCI MUE table") and ans.citations[0].chunk.pages == "MUE 64450"
