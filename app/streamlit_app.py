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
st.caption(
    "Answers come only from the manual (cited by chapter, section, and page) and, for specific codes, "
    "the CMS NCCI edit tables (cited by file version and edit)."
)

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
        "- How are add-on codes handled?\n"
        "- Can 29880 and 29881 be reported together?  _(edit tables)_\n"
        "- What is the MUE for 64450?  _(edit tables)_"
    )
    st.caption("Edit tables loaded: " + ("yes" if Path("data/edits.sqlite").exists() else "no (run `python -m ncci_rag load-edits`)"))

try:
    qa = load_pipeline()
except Exception as e:  # missing index or key: show how to fix it
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


for turn in st.session_state.history:
    with st.chat_message(turn["role"]):
        if turn["role"] == "user":
            st.markdown(turn["content"])
        else:
            render_answer(turn["answer"], turn.get("result"), debug)

question = st.chat_input("Ask about NCCI coding policy...")
if question:
    st.session_state.history.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Searching the manual..."):
            answer, result = qa.ask(question, None if chapter == "All" else chapter)
        render_answer(answer, result, debug)
    st.session_state.history.append({"role": "assistant", "answer": answer, "result": result})
