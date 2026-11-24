"""Citation text built from chunk metadata (models.py)."""

from ncci_rag.models import Chunk

from conftest import make_chunk


def test_citation_heading_and_pages():
    c = make_chunk("I.E.01", "x", title="Modifiers and Modifier Indicators")
    assert c.heading == "Chapter I (General Correct Coding Policies) – Section E. Modifiers and Modifier Indicators"
    assert c.pages == "p. I-14 (PDF p. 30)"
    span = Chunk("IV.E.01", "IV", "Surgery", "CPT Codes 20000 - 29999", "E", "Arthroscopy", 87, 88, "IV-5", "IV-6", "x")
    assert span.pages == "pp. IV-5–IV-6 (PDF pp. 87–88)"
    assert span.context_header.endswith("[CPT Codes 20000 - 29999]")
    intro = Chunk("Intro.purpose.01", "Intro", "Introduction", None, "purpose", "Purpose", 5, 5, "Intro-1", "Intro-1", "x")
    assert intro.heading == "Introduction (Introduction) – Purpose"


def test_fact_chunks_cite_the_table_not_a_page():
    fact = Chunk("MUE.64450", "MUE", "Medicare NCCI MUE table (practitioner)", None, "", "MUE 64450", 0, 0, "", "", "x", kind="mue")
    assert fact.is_fact and fact.heading == "Medicare NCCI MUE table (practitioner)" and fact.pages == "MUE 64450"
