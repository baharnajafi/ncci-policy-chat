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
# is usually no secrets file and .env is used instead. Reading st.secrets without a file
# shows a red "No secrets found" box even when the error is caught, so probe first.
with contextlib.suppress(Exception):
    if st.secrets.load_if_toml_exists():
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
def _secret(name: str) -> str | None:
    """Read a secret live from st.secrets (so an edit in the platform's settings applies
    without a reboot), falling back to the environment for local runs."""
    with contextlib.suppress(Exception):
        if st.secrets.load_if_toml_exists() and name in st.secrets:
            return str(st.secrets[name]).strip() or None
    return os.getenv(name)


if not st.session_state.get("authenticated"):
    expected = _secret("APP_PASSWORD")
    if password_ok(None, expected):
        st.session_state.authenticated = True
    else:
        with st.form("login"):
            given = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Enter")
        if submitted and password_ok(given, expected):
            st.session_state.authenticated = True
            st.rerun()
        if submitted:
            st.error("Wrong password.")
        st.stop()

settings = get_settings()
CHAPTERS = ["All", "Intro", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII", "XIII"]


@st.cache_resource(show_spinner="First start: downloading the manual and building the index (about a minute)...")
def load_pipeline() -> QAPipeline:
    s = get_settings()
    ensure_ready(s, log=lambda msg: None)
    return QAPipeline(s)


# Sidebar examples, grouped by what they demonstrate. The negative groups come from
# eval/questions.jsonl, where each one is labelled and graded.
EXAMPLES = [
    ("Answered from the manual", "Each sentence cites chapter, section, and page; click a citation for the exact quote.", [
        ("When is modifier 59 appropriate, and what are XE, XS, XP, XU?", "cites Chapter I, Section E"),
        ("Can an E&M service be reported on the same day as a minor surgical procedure?", "modifier 25, significant and separately identifiable"),
        ("If a diagnostic arthroscopy leads to a surgical arthroscopy, can both be reported?", "only the surgical one; Chapter IV, Section E"),
    ]),
    ("Off-topic: refused before the LLM", "The relevance gate blocks these, so no model call is made. Calibrated on 10 such questions.", [
        ("What is the 2026 Medicare Part B monthly premium?", "Medicare words, but not in the manual: refused"),
        ("Which hospitals in Texas have the best cardiology ratings?", "highest-scoring off-topic question (0.05): a gate at 0.05 would pass it; the default 0.30 keeps a wide margin"),
    ]),
    ("Coding questions the manual can't answer", "Hard negatives: on-topic, but the value lives in another CMS source. The app must not invent it.", [
        ("How many days is the global surgical period for CPT 27447?", "the manual explains global periods but never names 27447: says so instead of '90 days'"),
        ("What are the 2026 work RVUs for CPT 99213?", "RVUs are in the fee schedule: refused, no number"),
        ("What is the timely filing limit for a corrected claim with modifier 59?", "passes the gate (on-topic) but the model abstains"),
    ]),
    ("Exact facts from the CMS edit tables", "Rows from the PTP and MUE files are cited next to the manual section that explains them.", [
        ("What is the MUE value for CPT 64450?", "10 units, from the MUE table. Before the claim check the app answered 'one', borrowed from trichiasis codes"),
        ("Can CPT 29880 and 29881 be reported together for the same knee?", "active PTP edit, modifier indicator 1, plus Chapter I, Section E"),
    ]),
]


def _ask(question: str) -> None:
    st.session_state.pending_question = question


asked = st.session_state.setdefault("asked", 0)
left = questions_left(asked, settings.max_questions_per_session)

with st.sidebar:
    chapter = st.selectbox("Limit to chapter", CHAPTERS, index=0)
    debug = st.toggle("Show retrieval details", value=False)
    st.markdown("**Try these** (turn on *Show retrieval details* to see the gate score and any removed sentences)")
    for group, intro, examples in EXAMPLES:
        if group == "Exact facts from the CMS edit tables" and not settings.edits_db.exists():
            continue
        st.markdown(f"**{group}**")
        st.caption(intro)
        for i, (q, look_for) in enumerate(examples):
            st.button(q, key=f"ex-{group}-{i}", on_click=_ask, args=(q,), disabled=left == 0, help=look_for)
            st.caption(f"↳ {look_for}")
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
if not question and left != 0:  # a sidebar example was clicked
    question = st.session_state.pop("pending_question", None)
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
