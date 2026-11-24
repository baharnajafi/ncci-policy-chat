"""End to end: QAPipeline.ask and build_index with fake models (pipeline.py).

These pin the behaviours a reviewer would ask about: the gate stops off-topic questions
*before* any LLM call; answers cite only passages that support them; facts from the
edit tables reach the model labelled F; and a mismatched or missing index fails loudly.
"""

import numpy as np
import pytest

import ncci_rag.pipeline as pipeline_mod
from ncci_rag.index.store import IndexStore
from ncci_rag.models import Paragraph, Section
from ncci_rag.pipeline import QAPipeline, build_index

from conftest import CORPUS, FakeChatClient, FakeEmbedder, source_id_containing

ME_QUOTE = "cannot reasonably be performed at the same anatomic site"
PTP_QUOTE = "Column One code 29880, Column Two code 29881"


def responder(prompt: str) -> dict:
    """Answer like the model would: quote a real sentence and cite the block it is in,
    plus one sentence with an invented quote that the claim check must remove."""
    sentences = []
    if ME_QUOTE in prompt:
        sentences.append({"quotes": [ME_QUOTE], "source_ids": [source_id_containing(prompt, ME_QUOTE)],
                          "text": "Mutually exclusive procedures cannot be performed at the same anatomic site."})
    if PTP_QUOTE in prompt:
        sentences.append({"quotes": [PTP_QUOTE], "source_ids": [source_id_containing(prompt, PTP_QUOTE)],
                          "text": "29880 is the Column One code and 29881 the Column Two code."})
    sentences.append({"quotes": ["this sentence is not in any source"], "source_ids": ["S1"], "text": "An invented claim."})
    return {"answerable": True, "sentences": sentences, "not_covered": "", "reason": ""}


@pytest.fixture
def client(monkeypatch):
    c = FakeChatClient(responder)
    monkeypatch.setattr(pipeline_mod, "get_client", lambda: c)
    monkeypatch.setattr(pipeline_mod, "OpenAIEmbedder", FakeEmbedder)
    return c


@pytest.fixture
def qa(store, settings, client):
    q = QAPipeline(settings)
    yield q
    q.close()


def test_off_topic_question_is_refused_without_calling_the_llm(qa, client):
    answer, result = qa.ask("What is the Part B monthly premium?")
    assert not result.passed_gate and not answer.answerable
    assert "couldn't find this" in answer.text and client.calls == []


def test_answer_cites_the_supporting_passage_and_drops_invented_claims(qa, client):
    answer, _ = qa.ask("Which procedures are mutually exclusive?")
    assert len(client.calls) == 1 and client.calls[0]["temperature"] == 0
    assert client.calls[0]["response_format"]["json_schema"]["strict"] is True
    assert answer.answerable and [c.chunk.chunk_id for c in answer.citations] == ["I.P.01"]
    assert "[1]" in answer.text and "invented" not in answer.text
    assert [r.text for r in answer.rejected] == ["An invented claim."]


def test_edit_table_facts_reach_the_model_labelled_f(store, settings, client, edit_graph):
    qa = QAPipeline(settings)  # settings.edits_db is where the edit_graph fixture wrote the tables
    assert qa.edits is not None
    answer, result = qa.ask("Can 29880 and 29881 be billed together?")
    prompt = client.calls[0]["messages"][-1]["content"]
    assert "[F1] Medicare NCCI PTP edits (practitioner, v323r0" in prompt and "[S1]" in prompt
    assert answer.citations[0].chunk.chunk_id == "PTP.29880-29881"
    assert answer.citations[0].source_id == "F1" and result.facts
    qa.close()


def test_index_built_with_another_embedding_model_is_refused(store, settings, client):
    from conftest import with_settings

    with pytest.raises(RuntimeError, match="re-run ingest"):
        QAPipeline(with_settings(settings, embed_model="text-embedding-3-large"))


def test_missing_index_says_how_to_build_it(tmp_path, settings, client):
    from conftest import with_settings

    with pytest.raises(FileNotFoundError, match="ingest"):
        QAPipeline(with_settings(settings, db_path=tmp_path / "nope.sqlite"))


def test_build_index_parses_chunks_embeds_and_records_meta(tmp_path, settings, monkeypatch):
    from conftest import with_settings

    pdf = tmp_path / "manual.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")
    sections = [Section("I", "General Correct Coding Policies", None, "E", "Modifiers",
                        [Paragraph(c.text, 30, "I-14") for c in CORPUS[:3]])]
    monkeypatch.setattr(pipeline_mod, "parse_manual", lambda path: sections)
    monkeypatch.setattr(pipeline_mod, "OpenAIEmbedder", FakeEmbedder)
    s = with_settings(settings, pdf_path=pdf, db_path=tmp_path / "built.sqlite")
    store = build_index(s, log=lambda *_: None)
    meta = store.meta()
    assert meta["embed_model"] == "fake-embed" and meta["n_chunks"] == len(store.chunks()) == 1
    assert meta["embed_dim"] == FakeEmbedder.dim and len(meta["pdf_sha256"]) == 64
    reopened = IndexStore(s.db_path)
    assert isinstance(reopened.chunks()[1].text, str)
    reopened.close()
    store.close()


def test_build_index_without_pdf_says_where_to_get_it(tmp_path, settings):
    from conftest import with_settings

    with pytest.raises(FileNotFoundError, match="README"):
        build_index(with_settings(settings, pdf_path=tmp_path / "missing.pdf"), log=lambda *_: None)


def test_vectors_are_unit_length(store):
    store._load_vectors()
    assert np.allclose(np.linalg.norm(store._matrix, axis=1), 1.0, atol=1e-5)
