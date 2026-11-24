"""Section-aware chunking (ingest/chunker.py)."""

from ncci_rag.ingest.chunker import chunk_sections
from ncci_rag.models import Paragraph, Section


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


def test_list_item_starts_a_new_chunk_and_tiny_tail_is_merged():
    intro = Paragraph(" ".join(["intro"] * 130), 10, "I-3")
    item = Paragraph("a. Modifier 25 " + " ".join(["detail"] * 150), 10, "I-3")
    tail = Paragraph("b. Short closing note.", 11, "I-4")  # a list item, but too small for its own chunk
    chunks = chunk_sections([Section("I", "T", None, "E", "Modifiers", [intro, item, tail])])
    assert [c.text.split("\n\n")[0][:3] for c in chunks] == ["int", "a. "]  # item starts chunk 2
    assert len(chunks) == 2 and chunks[-1].text.endswith("b. Short closing note.")  # tiny tail merged
    assert (chunks[-1].label_start, chunks[-1].label_end) == ("I-3", "I-4")
    assert chunks[1].modifiers == ["25"]
