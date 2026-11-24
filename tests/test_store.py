"""The SQLite index: FTS5 keyword search, vectors, code index (index/store.py)."""

import numpy as np

from ncci_rag.index.store import IndexStore, fts_query

from conftest import CORPUS, make_chunk


def test_fts_query_is_safe():
    q = fts_query('What is "modifier" 59 AND NOT (x)?')
    assert '"59"' in q and '"modifier"' in q and "NOT" not in q.replace('"NOT"', "")
    assert fts_query("what is the") == ""  # only stopwords


def test_keyword_vector_and_code_search(tmp_path):
    chunks = [
        make_chunk("I.E.01", "Modifier 59 indicates a distinct procedural service."),
        make_chunk("I.V.01", "Medically Unlikely Edits limit units of service.", section="V"),
        make_chunk("II.B.01", "Peripheral nerve blocks, CPT codes 64400-64530, may be reported.", chapter="II", section="B"),
    ]
    store = IndexStore.build(tmp_path / "i.sqlite", chunks, np.eye(3, dtype=np.float32), {"embed_model": "fake"})
    ids = {r: c.chunk_id for r, c in store.chunks().items()}
    assert ids[store.keyword_search("units of service", 3)[0]] == "I.V.01"
    assert store.keyword_search("units of service", 3, chapter="II") == []
    assert ids[store.code_search([], ["59"], 3)[0]] == "I.E.01"
    assert ids[store.code_search(["64450"], [], 3)[0]] == "II.B.01"  # via the range 64400-64530
    assert ids[store.vector_search(np.array([0, 0, 1], dtype=np.float32), 1)[0][0]] == "II.B.01"
    assert [ids[r] for r, _ in store.vector_search(np.array([1, 0, 0], dtype=np.float32), 5, chapter="II")] == ["II.B.01"]
    store.close()


def test_build_is_atomic_and_round_trips(store):
    assert not store.path.with_suffix(".building").exists()
    assert store.meta() == {"embed_model": "fake-embed"}
    assert [c.chunk_id for c in store.chunks().values()] == [c.chunk_id for c in CORPUS]
    assert store.chapter_ranges() == {"II": ("00000", "01999"), "IV": ("20000", "29999")}


def test_section_search_only_returns_the_given_sections(store):
    rows = store.section_search(np.ones(512, dtype=np.float32) / np.sqrt(512), {"I.E", "I.P"}, 10)
    assert sorted(store.chunks()[r].chunk_id for r in rows) == ["I.E.01", "I.P.01"]
