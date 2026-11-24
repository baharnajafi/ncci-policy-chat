"""Objects created on one thread must work from others, at the same time (index/db.py).

Regression test for a bug found by running the app as a hosted platform would: the
pipeline is cached once by Streamlit, but each rerun runs on a new thread, so the
second question of a session failed with "SQLite objects created in a thread can only
be used in that same thread" (the embedding cache used a plain sqlite3 connection).
"""

from concurrent.futures import ThreadPoolExecutor

import ncci_rag.llm_client as llm_client
from ncci_rag.index.embedder import OpenAIEmbedder
from ncci_rag.retrieval.hybrid import HybridRetriever

from conftest import FakeEmbedder


def test_retrieval_store_and_edit_graph_from_many_threads(store, settings, edit_graph):
    retriever = HybridRetriever(store, FakeEmbedder(), settings, edit_graph)  # created on this thread
    questions = ["Which procedures are mutually exclusive?", "Can 29880 and 29881 be billed together?",
                 "What is the MUE for 64450?", "When is modifier XS used?"] * 10
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(retriever.retrieve, questions))
    assert [r.passages[0].chunk.chunk_id for r in results[:4]] == \
           [r.passages[0].chunk.chunk_id for r in results[4:8]]  # same answers under concurrency
    assert all(r.facts for r in results[1::4]) and all(r.facts for r in results[2::4])


def test_embedding_cache_from_another_thread(tmp_path, monkeypatch):
    from types import SimpleNamespace

    client = SimpleNamespace(embeddings=SimpleNamespace(
        create=lambda model, input: SimpleNamespace(data=[SimpleNamespace(embedding=[1.0, float(len(t))]) for t in input])))
    monkeypatch.setattr(llm_client, "get_client", lambda: client)
    e = OpenAIEmbedder("m", cache_path=tmp_path / "cache.sqlite")  # created on this thread
    e.embed(["first question"])
    with ThreadPoolExecutor(max_workers=4) as pool:  # later questions arrive on other threads
        vecs = list(pool.map(lambda t: e.embed([t]), ["first question", "second", "third", "second"] * 5))
    assert len(vecs) == 20 and all(v.shape == (1, 2) for v in vecs)
    e.close()


def test_cold_store_loaded_by_many_threads_at_once(store):
    """Regression test for a race seen in CI (Python 3.12): lazy loading published an
    empty dict before filling it, so a second thread could look up a chunk too early
    (KeyError). A barrier releases all threads together against a freshly opened store."""
    import threading

    from ncci_rag.index.store import IndexStore

    for _ in range(20):
        cold = IndexStore(store.path)
        barrier = threading.Barrier(16)

        def read(_, cold=cold, barrier=barrier):
            barrier.wait()
            rowids, matrix = cold._vectors()
            chunks = cold.chunks()
            return len(chunks), len(rowids), matrix.shape[0], all(int(r) in chunks for r in rowids)

        with ThreadPoolExecutor(max_workers=16) as pool:
            results = set(pool.map(read, range(16)))
        cold.close()
        assert results == {(7, 7, 7, True)}
