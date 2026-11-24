"""Embedding cache and retries (index/embedder.py), the LLM client switch (llm_client.py),
and the command-line interface (__main__.py)."""

from types import SimpleNamespace

import numpy as np
import openai
import pytest

import ncci_rag.index.embedder as embedder_mod
import ncci_rag.llm_client as llm_client
from ncci_rag.__main__ import main
from ncci_rag.index.embedder import OpenAIEmbedder


class FakeEmbeddingsClient:
    """``client.embeddings.create`` that can fail a few times before answering."""

    def __init__(self, failures: list[Exception] | None = None):
        self.failures = list(failures or [])
        self.batches: list[list[str]] = []
        self.embeddings = SimpleNamespace(create=self._create)

    def _create(self, model, input):
        if self.failures:
            raise self.failures.pop(0)
        self.batches.append(list(input))
        return SimpleNamespace(data=[SimpleNamespace(embedding=[float(len(t)), 1.0, 0.0]) for t in input])


@pytest.fixture
def fake_openai(monkeypatch):
    def install(client):
        monkeypatch.setattr(llm_client, "get_client", lambda: client)
        monkeypatch.setattr(embedder_mod.time, "sleep", lambda s: None)
        return client
    return install


def _status_error(cls, code: int):
    """An SDK error instance without building an HTTP response (the SDK's HTTP library
    changes between major versions; the embedder only reads the class and status_code)."""
    err = cls.__new__(cls)
    Exception.__init__(err, f"HTTP {code}")
    err.status_code = code
    return err


def test_cache_means_each_text_is_embedded_once(tmp_path, fake_openai):
    client = fake_openai(FakeEmbeddingsClient())
    e = OpenAIEmbedder("m", cache_path=tmp_path / "cache.sqlite", batch_size=2)
    first = e.embed(["a", "bb", "ccc", "dddd", "eeeee"])
    e.close()
    assert [len(b) for b in client.batches] == [2, 2, 1]  # batched
    assert np.allclose(np.linalg.norm(first, axis=1), 1.0)  # normalised
    e2 = OpenAIEmbedder("m", cache_path=tmp_path / "cache.sqlite")
    second = e2.embed(["bb", "ffffff"])
    e2.close()
    assert client.batches[-1] == ["ffffff"]  # only the new text hits the API, even after a restart
    assert np.allclose(second[0], first[1])
    e3 = OpenAIEmbedder("other-model", cache_path=tmp_path / "cache.sqlite")
    e3.embed(["bb"])
    e3.close()
    assert client.batches[-1] == ["bb"]  # the cache is keyed by model too


def test_transient_errors_are_retried_then_raised(fake_openai):
    client = fake_openai(FakeEmbeddingsClient([_status_error(openai.RateLimitError, 429),
                                               _status_error(openai.InternalServerError, 500)]))
    assert OpenAIEmbedder("m").embed(["x"]).shape == (1, 3) and client.batches == [["x"]]

    fake_openai(FakeEmbeddingsClient([_status_error(openai.RateLimitError, 429)] * 3))
    with pytest.raises(openai.RateLimitError):
        OpenAIEmbedder("m", max_retries=3).embed(["x"])

    fake_openai(FakeEmbeddingsClient([_status_error(openai.BadRequestError, 400)]))
    with pytest.raises(openai.BadRequestError):  # a client error is not retried
        OpenAIEmbedder("m").embed(["x"])


def test_client_switches_between_openai_and_azure(monkeypatch):
    llm_client.get_client.cache_clear()
    monkeypatch.delenv("AZURE_OPENAI_ENDPOINT", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        llm_client.get_client()
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example.openai.azure.com")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "test-key")
    assert isinstance(llm_client.get_client(), openai.AzureOpenAI)
    llm_client.get_client.cache_clear()


def test_cli_load_edits_and_ask(edit_zips, tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("NCCI_EDITS_DIR", str(edit_zips))
    monkeypatch.setenv("NCCI_EDITS_DB", str(tmp_path / "cli-edits.sqlite"))
    assert main(["load-edits"]) == 0 and (tmp_path / "cli-edits.sqlite").exists()

    from ncci_rag.models import Answer, AnswerSentence, Citation, RejectedSentence, ScoredChunk
    from ncci_rag.retrieval.hybrid import RetrievalResult

    from conftest import make_chunk

    chunk = make_chunk("I.E.01", "Modifier 59 marks a distinct service.")
    answer = Answer("q", True, [AnswerSentence("Modifier 59 marks a distinct service.", ["S1"], ["Modifier 59"])],
                    [Citation("S1", chunk)], [], rejected=[RejectedSentence("Bad claim.", "no valid source")])
    result = RetrievalResult([ScoredChunk(chunk, 0.9, {"keyword": 1})], 0.9, True, [], ["59"], None)

    class FakeQA:
        def __init__(self, settings):
            pass

        def ask(self, question, chapter=None):
            return answer, result

    import ncci_rag.pipeline as pipeline_mod

    monkeypatch.setattr(pipeline_mod, "QAPipeline", FakeQA)
    assert main(["ask", "--debug", "When is modifier 59 used?"]) == 0
    out = capsys.readouterr().out
    assert "Modifier 59 marks a distinct service. [1]" in out
    assert "[1] Chapter I (General Correct Coding Policies) – Section E. Modifiers, p. I-14" in out
    assert "Removed by the claim check" in out and "gate=pass" in out and "I.E.01" in out
