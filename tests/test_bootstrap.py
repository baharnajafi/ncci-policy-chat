"""First-run setup and access control for the hosted app (bootstrap.py)."""

import os

import pytest

import ncci_rag.bootstrap as boot
import ncci_rag.pipeline as pipeline_mod
from ncci_rag.models import Paragraph, Section

from conftest import FakeEmbedder, with_settings


def test_secrets_are_copied_to_env_without_overriding(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("NCCI_TOP_K", raising=False)
    monkeypatch.setenv("NCCI_RERANKER", "already-set")
    applied = boot.apply_secrets({"OPENAI_API_KEY": "sk-test", "NCCI_TOP_K": 4, "NCCI_RERANKER": "other",
                                  "UNRELATED": "x", "APP_PASSWORD": "  "})
    assert applied == ["OPENAI_API_KEY", "NCCI_TOP_K"]  # names only; blank and unknown keys ignored
    assert os.environ["OPENAI_API_KEY"] == "sk-test" and os.environ["NCCI_TOP_K"] == "4"
    assert os.environ["NCCI_RERANKER"] == "already-set" and "UNRELATED" not in os.environ


def test_password_and_question_limit():
    assert boot.password_ok(None, None) and boot.password_ok("anything", "")
    assert boot.password_ok("s3cret", "s3cret")
    assert not boot.password_ok("wrong", "s3cret") and not boot.password_ok(None, "s3cret")
    assert boot.questions_left(5, 0) is None  # unlimited
    assert boot.questions_left(3, 25) == 22 and boot.questions_left(30, 25) == 0


def test_first_start_downloads_the_pdf_and_builds_the_index(tmp_path, settings, monkeypatch):
    fetched = []

    def fake_fetch(url, dest):
        fetched.append(url)
        dest.write_bytes(b"%PDF-1.4 fake")

    monkeypatch.setattr(pipeline_mod, "OpenAIEmbedder", FakeEmbedder)
    monkeypatch.setattr(pipeline_mod, "parse_manual", lambda path: [
        Section("I", "General", None, "E", "Modifiers", [Paragraph("Modifier 59 marks a distinct service.", 30, "I-14")])])
    s = with_settings(settings, pdf_path=tmp_path / "data" / "manual.pdf", db_path=tmp_path / "data" / "index.sqlite")

    assert boot.ensure_ready(s, log=lambda m: None, fetch=fake_fetch) == "built"
    assert fetched == [boot.MANUAL_URL] and s.db_path.exists()
    assert boot.ensure_ready(s, log=lambda m: None, fetch=fake_fetch) == "ready"  # second start reuses it
    assert len(fetched) == 1

    other_model = with_settings(s, embed_model="another-model")
    assert not boot.index_is_current(other_model)  # an index from another embedding model is rebuilt


def test_download_rejects_a_non_pdf_and_leaves_nothing(tmp_path, monkeypatch):
    class Resp:
        def __init__(self, body):
            self.body = body

        def read(self):
            return self.body

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    dest = tmp_path / "manual.pdf"
    monkeypatch.setattr(boot.urllib.request, "urlopen", lambda req, timeout: Resp(b"<html>moved</html>"))
    with pytest.raises(RuntimeError, match="did not return a PDF"):
        boot.download("https://example.test/x.pdf", dest)
    assert not dest.exists() and not list(tmp_path.glob("*.part"))

    monkeypatch.setattr(boot.urllib.request, "urlopen", lambda req, timeout: Resp(b"%PDF-1.7 ok"))
    boot.download("https://example.test/x.pdf", dest)
    assert dest.read_bytes().startswith(b"%PDF-")
