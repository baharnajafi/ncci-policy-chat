"""The PDF parser on the real manual. Skipped when the PDF is not downloaded (e.g. in CI)."""

from pathlib import Path

import pytest

PDF = Path(__file__).resolve().parents[1] / "data" / "2026_ncci_medicare_policy_manual_all-chapters.pdf"


@pytest.fixture(scope="module")
def sections():
    from ncci_rag.ingest.pdf_parser import parse_manual

    return parse_manual(PDF)


pytestmark = pytest.mark.skipif(not PDF.exists(), reason="manual PDF not downloaded")


def test_sections_chapters_and_page_labels(sections):
    keys = {f"{s.chapter_id}.{s.section_id}" for s in sections}
    assert {"I.E", "I.V", "IV.E", "IX.B", "XIII.E", "Intro.purpose"} <= keys
    ch4 = next(s for s in sections if s.chapter_id == "IV")
    assert ch4.code_range and "20000" in ch4.code_range
    mods = next(s for s in sections if s.chapter_id == "I" and s.section_id == "E")
    assert mods.paragraphs[0].page_label.startswith("I-")
    # Table-of-contents pages are skipped: no paragraph is a run of "... I-26" entries.
    assert not any(p.text.count(" I-") > 5 for s in sections for p in s.paragraphs)


def test_rationale_links_point_at_matching_sections(sections):
    """Graph links: each PTP rationale must point at the Chapter I section with that topic."""
    from ncci_rag.edits.graph import MODIFIER_SECTION, MUE_SECTION, RATIONALE_SECTIONS

    titles = {f"{s.chapter_id}.{s.section_id}": s.section_title.lower() for s in sections}
    assert "modifier" in titles[MODIFIER_SECTION] and "medically unlikely" in titles[MUE_SECTION]
    for rationale, sec in RATIONALE_SECTIONS.items():
        words = [w for w in rationale.replace("/", " ").split() if len(w) > 5 and w not in {"manual", "column"}]
        assert any(w in titles[sec] for w in words), (rationale, sec, titles[sec])
