"""Minimal chat UI. Run: streamlit run app/streamlit_app.py

Deliberately simple: the point of the exercise is retrieval and grounding, so the UI
shows the answer, numbered citations you can expand to read the exact passage, and
an optional retrieval-debug view (scores and per-retriever ranks).
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ncci_rag.config import get_settings  # noqa: E402
from ncci_rag.pipeline import QAPipeline  # noqa: E402

st.set_page_config(page_title="NCCI Policy Manual Chat", layout="centered")
st.title("Medicare NCCI Policy Manual (2026)")
st.caption("Answers come only from the manual, with citations to chapter, section, and page.")

CHAPTERS = ["All", "Intro", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII", "XIII"]


@st.cache_resource
def load_pipeline() -> QAPipeline:
    return QAPipeline(get_settings())


with st.sidebar:
    chapter = st.selectbox("Limit to chapter", CHAPTERS, index=0)
    debug = st.toggle("Show retrieval details", value=False)
    st.markdown(
        "Examples:\n"
        "- When is modifier 59 appropriate, and what are XE, XS, XP, XU?\n"
        "- What is a Medically Unlikely Edit?\n"
        "- Can an E&M service be reported on the same day as a minor procedure?\n"
        "- How are add-on codes handled?"
    )

try:
    qa = load_pipeline()
except Exception as e:  # missing index or key: show how to fix it
    st.error(str(e))
    st.stop()

if "history" not in st.session_state:
    st.session_state.history = []

for turn in st.session_state.history:
    with st.chat_message(turn["role"]):
        st.markdown(turn["content"])

question = st.chat_input("Ask about NCCI coding policy...")
if question:
    st.session_state.history.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Searching the manual..."):
            answer, result = qa.ask(question, None if chapter == "All" else chapter)
        st.markdown(answer.text)
        for i, c in enumerate(answer.citations, start=1):
            with st.expander(f"[{i}] {c.chunk.heading}, {c.chunk.pages}"):
                st.write(c.chunk.text)
        if debug:
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
    st.session_state.history.append({"role": "assistant", "content": answer.text})
