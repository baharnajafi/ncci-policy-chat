"""Shared fixtures. Every test runs offline: no API key, no network, no model download.

The fakes are small but behave like the real components in the ways the code depends on:

* ``FakeEmbedder``: hashed bag-of-words vectors, L2-normalised. Texts that share words
  have positive cosine similarity; texts that share none are near zero. That is enough
  to exercise dense retrieval, chapter routing, and the no-reranker gate.
* ``FakeReranker``: fraction of question words found in the passage (0-1), the same
  scale as the real cross-encoder after its sigmoid.
* ``FakeChatClient``: records every call and answers with a JSON body built by a
  test-supplied ``responder``, in the structured-output shape the pipeline expects.
"""

from __future__ import annotations

import hashlib
import json
import re
import zipfile
from dataclasses import replace
from types import SimpleNamespace

import numpy as np
import pytest

from ncci_rag.config import Settings
from ncci_rag.index.store import IndexStore
from ncci_rag.ingest.codes import find_codes, find_modifiers
from ncci_rag.models import Chunk

STOP = {"a", "an", "and", "are", "at", "be", "can", "for", "if", "in", "is", "it", "of", "on", "or", "the", "to", "what", "which", "with"}


def words(text: str) -> list[str]:
    return [w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in STOP]


class FakeEmbedder:
    model = "fake-embed"
    dim = 512

    def __init__(self, *_, **__):
        self.calls = 0

    def embed(self, texts: list[str]) -> np.ndarray:
        self.calls += 1
        out = np.zeros((len(texts), self.dim), dtype=np.float32)
        for i, t in enumerate(texts):
            for w in words(t):
                out[i, int(hashlib.md5(w.encode()).hexdigest(), 16) % self.dim] += 1.0
        norms = np.linalg.norm(out, axis=1, keepdims=True)
        return out / np.clip(norms, 1e-12, None)

    def close(self) -> None:
        pass


class FakeReranker:
    def score(self, query: str, passages: list[str]) -> list[float]:
        q = set(words(query))
        return [len(q & set(words(p))) / max(len(q), 1) for p in passages]


class FakeChatClient:
    """Mimics ``client.chat.completions.create(...)``."""

    def __init__(self, responder):
        self.responder = responder
        self.calls: list[dict] = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        prompt = kwargs["messages"][-1]["content"]
        body = json.dumps(self.responder(prompt))
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=body))])


def source_id_containing(prompt: str, text: str) -> str:
    """The [S1]/[F1] label of the source block in the prompt that contains ``text``."""
    for label, body in re.findall(r"\[([SF]\d+)\] (.*?)(?=\n\n---\n\n\[|\Z)", prompt, re.S):
        if text in body:
            return label
    raise AssertionError(f"{text!r} not in any source")


def make_chunk(cid: str, text: str, chapter: str = "I", section: str = "E", title: str = "Modifiers",
               chapter_title: str = "General Correct Coding Policies", code_range: str | None = None) -> Chunk:
    return Chunk(cid, chapter, chapter_title, code_range, section, title, 30, 30, f"{chapter}-14", f"{chapter}-14",
                 text, find_codes(text), find_modifiers(text))


CORPUS = [
    make_chunk("I.E.01", "Modifier 59 and modifiers XE, XS, XP, and XU indicate a distinct procedural service. "
               "A modifier indicator of 1 allows an NCCI PTP-associated modifier to bypass the edit."),
    make_chunk("I.H.01", "A HCPCS/CPT code descriptor defines the procedure. Services included in the code descriptor "
               "are not reported separately.", section="H", title="HCPCS/CPT Procedure Code Definition"),
    make_chunk("I.P.01", "Mutually exclusive procedures cannot reasonably be performed at the same anatomic site "
               "or the same patient encounter.", section="P", title="Mutually Exclusive Procedures"),
    make_chunk("I.V.01", "Medically Unlikely Edits define the maximum units of service for a code on a date of service.",
               section="V", title="Medically Unlikely Edits (MUEs)"),
    make_chunk("II.B.01", "Peripheral nerve blocks, CPT codes 64400-64530, may be reported for postoperative pain "
               "management.", chapter="II", section="B", title="Standard Anesthesia Coding",
               chapter_title="Anesthesia Services", code_range="CPT Codes 00000 - 01999"),
    make_chunk("IV.E.01", "If a diagnostic arthroscopy leads to a surgical arthroscopy at the same encounter, only the "
               "surgical arthroscopy is reported.", chapter="IV", section="E", title="Arthroscopy",
               chapter_title="Surgery: Musculoskeletal System", code_range="CPT Codes 20000 - 29999"),
    make_chunk("IV.E.02", "Knee arthroscopy codes include debridement and shaving of articular cartilage in the same "
               "compartment.", chapter="IV", section="E", title="Arthroscopy",
               chapter_title="Surgery: Musculoskeletal System", code_range="CPT Codes 20000 - 29999"),
]


@pytest.fixture
def store(tmp_path):
    vecs = FakeEmbedder().embed([f"{c.context_header}\n\n{c.text}" for c in CORPUS])
    s = IndexStore.build(tmp_path / "index.sqlite", CORPUS, vecs, {"embed_model": FakeEmbedder.model})
    yield s
    s.close()


@pytest.fixture
def settings(tmp_path) -> Settings:
    return Settings(
        db_path=tmp_path / "index.sqlite", edits_db=tmp_path / "edits.sqlite", edits_dir=tmp_path / "edits",
        cache_path=tmp_path / "cache.sqlite", embed_model=FakeEmbedder.model, reranker_model="none",
        candidates_per_retriever=10, rerank_pool=10, top_k=3, min_relevance=0.3, min_dense_similarity=0.2,
    )


def with_settings(s: Settings, **changes) -> Settings:
    return replace(s, **changes)


# ---------------------------------------------------------------- CMS edit files
PTP_TXT = (
    "CPT only copyright 2025 American Medical Association.\t\t\t\t\t\t\r\n"
    "Column 1\tColumn 2\t*=in existence\tEffective\tDeletion\tModifier\tPTP Edit Rationale\r\n"
    "29880\t29881\t\t19960101\t*\t1\tHCPCS/CPT procedure code definition\r\n"
    "0001A\t0591T\t\t20220101\t20231231\t1\tCPT Manual or CMS manual coding instruction\r\n"
    "29880\t20610\t\t20000101\t*\t1\tMutually exclusive procedures\r\n"
)
MUE_CSV = ('copyright text,,,\r\n"HCPCS/\r\nCPT Code",MUE Values,MUE Adjudication Indicator,MUE Rationale\r\n'
           "64450,10,3 Date of Service Edit: Clinical,Clinical: Data\r\n")


@pytest.fixture
def edit_zips(tmp_path):
    """Tiny files in the CMS layouts (tab-separated PTP TXT, MUE CSV), zipped like the real downloads."""
    d = tmp_path / "edits"
    d.mkdir(exist_ok=True)
    with zipfile.ZipFile(d / "ptp-f1.zip", "w") as z:
        z.writestr("ccipra-v323r0-f1.TXT", PTP_TXT)
    with zipfile.ZipFile(d / "mue.zip", "w") as z:
        z.writestr("MCR_MUE_PractitionerServices_Eff_10-01-2026.csv", MUE_CSV)
    return d


@pytest.fixture
def edit_graph(edit_zips, tmp_path):
    from ncci_rag.edits.graph import EditGraph
    from ncci_rag.edits.loader import load_edits

    g = EditGraph(load_edits(edit_zips, tmp_path / "edits.sqlite", log=lambda *_: None))
    yield g
    g.close()
