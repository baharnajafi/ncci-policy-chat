"""Minimal chat UI. Run: streamlit run app/streamlit_app.py

Deliberately simple: the point of the exercise is retrieval and grounding, so the UI
shows the answer, numbered citations you can expand to read the exact passage, and
an optional retrieval-debug view (scores and per-retriever ranks).

Hosted use (see docs/DEPLOY.md): secrets come from the platform's secret store; the
first start downloads the manual and builds the index; an optional shared password
and a per-session question limit protect the API key.
"""

from __future__ import annotations

import contextlib
import os
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)  # data/ paths are relative to the repository root, wherever the app is started from
sys.path.insert(0, str(ROOT / "src"))

from ncci_rag.bootstrap import apply_secrets, ensure_ready, password_ok, questions_left  # noqa: E402

# Streamlit secrets (hosted) -> environment, before any settings are read. Locally there
# is usually no secrets file, and .env is used instead.
with contextlib.suppress(Exception):
    apply_secrets(dict(st.secrets))

from ncci_rag.config import get_settings  # noqa: E402
from ncci_rag.pipeline import QAPipeline  # noqa: E402

st.set_page_config(page_title="NCCI Policy Manual Chat", layout="centered")
st.title("Medicare NCCI Policy Manual (2026)")
st.caption(
    "Answers come only from the manual (cited by chapter, section, and page) and, for specific codes, "
    "the CMS NCCI edit tables when they are loaded (cited by file version and edit)."
)

# ---------------------------------------------------------------- access
if not st.session_state.get("authenticated"):
    expected = os.getenv("APP_PASSWORD")
    if password_ok(None, expected):
        st.session_state.authenticated = True
    else:
        given = st.text_input("Password", type="password")
        if given and password_ok(given, expected):
            st.session_state.authenticated = True
            st.rerun()
        if given:
            st.error("Wrong password.")
        st.stop()

settings = get_settings()
CHAPTERS = ["All", "Intro", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII", "XIII"]


@st.cache_resource(show_spinner="First start: downloading the manual and building the index (about a minute)...")
def load_pipeline() -> QAPipeline:
    s = get_settings()
    ensure_ready(s, log=lambda msg: None)
    return QAPipeline(s)


asked = st.session_state.setdefault("asked", 0)
left = questions_left(asked, settings.max_questions_per_session)

with st.sidebar:
    chapter = st.selectbox("Limit to chapter", CHAPTERS, index=0)
    debug = st.toggle("Show retrieval details", value=False)
    st.markdown(
        "Examples:\n"
        "- When is modifier 59 appropriate, and what are XE, XS, XP, XU?\n"
        "- What is a Medically Unlikely Edit?\n"
        "- Can an E&M service be reported on the same day as a minor procedure?\n"
        "- How are add-on codes handled?\n"
        "- Can 29880 and 29881 be reported together?  _(edit tables)_\n"
        "- What is the MUE for 64450?  _(edit tables)_"
    )
    st.caption("Edit tables loaded: " + ("yes" if settings.edits_db.exists() else "no (manual only)"))
    if left is not None:
        st.caption(f"Questions left in this session: {left}")

try:
    qa = load_pipeline()
except Exception as e:  # noqa: BLE001 - missing key, PDF, or index: show how to fix it
    st.error(str(e))
    st.stop()

if "history" not in st.session_state:
    st.session_state.history = []


def render_answer(answer, result=None, debug=False) -> None:
    """Answer text, then one expander per citation with the quotes that support it
    and the full passage. Kept in history so citations survive Streamlit reruns."""
    st.markdown(answer.text)
    for i, c in enumerate(answer.citations, start=1):
        quotes = [q for s in answer.sentences if c.source_id in s.source_ids for q in s.quotes]
        with st.expander(f"[{i}] {c.chunk.heading}, {c.chunk.pages}"):
            for q in dict.fromkeys(quotes):
                st.markdown(f"> {q}")
            st.caption("Full passage")
            st.write(c.chunk.text)
    if debug and answer.rejected:
        st.caption("Removed by the claim check:")
        for r in answer.rejected:
            st.markdown(f"- ~~{r.text}~~ — _{r.reason}_")
    if debug and result is not None and result.facts:
        st.caption("Edit-table facts (graph lookup) and the manual sections they link to:")
        for f in result.facts:
            st.markdown(f"- `{f.chunk.chunk_id}` → {', '.join(f.linked_sections) or '—'}")
    if debug and result is not None:
        st.caption(
            f"Top relevance {result.top_relevance:.3f} (gate {'passed' if result.passed_gate else 'failed'}); "
            f"codes {result.query_codes}, modifiers {result.query_modifiers}, routed chapter {result.routed_chapter}"
        )
        st.table(
            [
                {"score": round(p.score, 3), "chunk": p.chunk.chunk_id, "pages": p.chunk.pages, "ranks": str(p.ranks)}
                for p in result.passages
            ]
        )


history = st.session_state.history
for i, turn in enumerate(history):
    with st.chat_message(turn["role"]):
        if turn["role"] == "user":
            st.markdown(turn["content"])
            # Streamlit stops a running answer when a new question arrives. A completed run
            # always stores the answer right after its question, so a question without one
            # was interrupted: say so instead of leaving it unanswered.
            answered = i + 1 < len(history) and history[i + 1]["role"] == "assistant"
            if not answered:
                st.caption("No answer: the next question was sent before this one finished. Ask it again if needed.")
        else:
            render_answer(turn["answer"], turn.get("result"), debug)

if left == 0:
    st.info("This session has reached its question limit. Open a new session to ask more.")
question = st.chat_input("Ask about NCCI coding policy...", disabled=left == 0)
if question:
    st.session_state.asked += 1
    st.session_state.history.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Searching the manual..."):
            answer, result = qa.ask(question, None if chapter == "All" else chapter)
        render_answer(answer, result, debug)
    st.session_state.history.append({"role": "assistant", "answer": answer, "result": result})
