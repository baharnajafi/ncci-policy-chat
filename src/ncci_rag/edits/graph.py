"""The NCCI edit tables, read as a small property graph, and linked to the manual.

Nodes and edges (stored as SQLite tables, not a graph database, see below):

    (Code)-[:PTP_EDIT {effective, deletion, modifier_indicator}]->(Code)   ptp table
    (PTP_EDIT)-[:BECAUSE]->(Rationale)-[:EXPLAINED_IN]->(Manual Section)  RATIONALE_SECTIONS
    (PTP_EDIT.modifier_indicator)-[:EXPLAINED_IN]->(Chapter I, Section E)
    (Code)-[:HAS_MUE {value, adjudication, rationale}]                     mue table
    (MUE)-[:EXPLAINED_IN]->(Chapter I, Section V)
    (Code)-[:IN_RANGE]->(Chapter)          (already in the index: chapter code ranges)
    (Section)-[:MENTIONS]->(Code)          (already in the index: code_mentions)

The edit files say *what* applies (is 93000/99214 an edit pair? which modifier
indicator? how many units?). The manual says *why*. A question about specific codes is
answered from both: the lookup returns **facts** (exact rows, rendered as short
citable passages), and each fact names the manual sections that explain it, which the
retriever then adds to its candidates (one hop of graph expansion).

Why tables and not Neo4j: every traversal here is one or two hops with an exact key
(a code or a code pair), which an indexed SQLite query answers in well under a
millisecond over 2.6M edges. A graph database pays off for variable-length traversals
(e.g. "all codes reachable through bundling chains") or when many more entity types
are joined (LCD/NCD coverage, fee schedule, OPPS status). See docs/DESIGN.md.

Date of service matters: the files keep deleted edits, and an edit applies only between
its effective and deletion dates. Lookups default to the file's effective date.
"""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass, field
from itertools import combinations
from pathlib import Path

from ..ingest.codes import find_codes
from ..models import Chunk

# PTP rationale -> the Chapter I section that explains it. The section ids are checked
# against the parsed manual in tests/test_core.py::test_parser_on_real_manual.
RATIONALE_SECTIONS = {
    "standards of medical/surgical practice": "I.B",
    "standard preparation/monitoring services for anesthesia": "I.F",
    "anesthesia service included in surgical procedure": "I.G",
    "hcpcs/cpt procedure code definition": "I.H",
    "cpt manual or cms manual coding instruction": "I.I",
    "cpt separate procedure definition": "I.J",
    "more extensive procedure": "I.L",
    "sequential procedure": "I.M",
    "laboratory panel": "I.N",
    "misuse of column two code with column one code": "I.O",
    "mutually exclusive procedures": "I.P",
}
MODIFIER_SECTION = "I.E"  # Modifiers and Modifier Indicators
MUE_SECTION = "I.V"  # Medically Unlikely Edits

MODIFIER_INDICATOR = {
    0: "0 (an NCCI PTP-associated modifier is not allowed; the edit cannot be bypassed)",
    1: "1 (an NCCI PTP-associated modifier is allowed to bypass the edit when clinically appropriate)",
    9: "9 (not applicable)",
}

MUE_INTENT = re.compile(r"\bMUEs?\b|medically unlikely|\bunits?\b|how many", re.I)
PTP_INTENT = re.compile(r"\bPTP\b|bundl|\bedits?\b|together|same day|column (?:one|two|1|2)", re.I)


@dataclass
class Fact:
    chunk: Chunk  # rendered as a citable passage (chunk.kind = "ptp" or "mue")
    linked_sections: list[str] = field(default_factory=list)  # manual sections that explain it, e.g. ["I.P", "I.E"]


def _date(d: int | None) -> str:
    return "none" if d is None else f"{d // 10000}-{d // 100 % 100:02d}-{d % 100:02d}"


class EditGraph:
    def __init__(self, db_path: Path):
        self.conn = sqlite3.connect(Path(db_path), check_same_thread=False)
        self.meta = dict(self.conn.execute("SELECT key, value FROM meta"))
        self.version = self.meta.get("ptp_version", "unknown version")
        self.effective = int(self.meta.get("ptp_effective") or 0)
        self.mue_effective = int(self.meta.get("mue_effective") or self.effective)
        self.ptp_source = f"Medicare NCCI PTP edits (practitioner, {self.version}, effective {_date(self.effective)})"
        self.mue_source = f"Medicare NCCI MUE table (practitioner services, effective {_date(self.mue_effective)})"

    # ------------------------------------------------------------------ queries
    def ptp_rows(self, a: str, b: str) -> list[tuple]:
        """Every edit between two codes, in either order, active or deleted."""
        return self.conn.execute(
            "SELECT col1, col2, effective, deletion, modifier_indicator, rationale FROM ptp "
            "WHERE (col1 = ? AND col2 = ?) OR (col1 = ? AND col2 = ?) ORDER BY effective DESC",
            (a, b, b, a),
        ).fetchall()

    def mue(self, code: str) -> tuple | None:
        return self.conn.execute("SELECT code, value, adjudication, rationale FROM mue WHERE code = ?", (code,)).fetchone()

    def neighbours(self, code: str, dos: int) -> dict:
        """One hop out from a code: how many active edits it has on each side, why, and examples."""
        active = "effective <= ? AND (deletion IS NULL OR deletion >= ?)"
        out = {}
        for side, other in (("col1", "col2"), ("col2", "col1")):
            out[side] = self.conn.execute(f"SELECT count(*) FROM ptp WHERE {side} = ? AND {active}", (code, dos, dos)).fetchone()[0]
            out[f"{side}_rationales"] = self.conn.execute(
                f"SELECT rationale, count(*) n FROM ptp WHERE {side} = ? AND {active} GROUP BY rationale ORDER BY n DESC LIMIT 3",
                (code, dos, dos),
            ).fetchall()
            out[f"{side}_examples"] = [r[0] for r in self.conn.execute(
                f"SELECT {other} FROM ptp WHERE {side} = ? AND {active} ORDER BY {other} LIMIT 8", (code, dos, dos))]
        return out

    # ------------------------------------------------------------------ facts
    def _fact(self, kind: str, key: str, location: str, text: str, linked: list[str]) -> Fact:
        source = self.ptp_source if kind == "ptp" else self.mue_source
        chunk = Chunk(
            chunk_id=f"{kind.upper()}.{key}", chapter_id=kind.upper(), chapter_title=source, code_range=None,
            section_id="", section_title=location, page_start=0, page_end=0, label_start="", label_end="",
            text=text, codes=find_codes(text), modifiers=[], kind=kind,
        )
        return Fact(chunk, list(dict.fromkeys(linked)))

    def pair_fact(self, a: str, b: str, dos: int) -> Fact:
        rows = self.ptp_rows(a, b)
        active = [r for r in rows if r[2] <= dos and (r[3] is None or r[3] >= dos)]
        if active:
            c1, c2, eff, dele, mi, rationale = active[0]
            text = (
                f"Medicare NCCI PTP edit (practitioner, {self.version}): Column One code {c1}, Column Two code {c2}. "
                f"Effective date {_date(eff)}; deletion date {_date(dele)}; the edit is active on {_date(dos)}. "
                f"If both codes are reported for the same beneficiary on the same date of service, the Column One code "
                f"{c1} is eligible for payment and the Column Two code {c2} is denied unless the edit is bypassed. "
                f"Modifier indicator {MODIFIER_INDICATOR.get(mi, str(mi))}. PTP edit rationale: {rationale}."
            )
            linked = [RATIONALE_SECTIONS.get(rationale.lower(), ""), MODIFIER_SECTION]
            return self._fact("ptp", f"{c1}-{c2}", f"edit {c1} / {c2}", text, [s for s in linked if s])
        if rows:
            c1, c2, eff, dele, mi, rationale = rows[0]
            text = (
                f"Medicare NCCI PTP edits (practitioner, {self.version}): the edit with Column One code {c1} and "
                f"Column Two code {c2} was effective {_date(eff)} and has deletion date {_date(dele)}, so it is not "
                f"active on {_date(dos)}. There is no active edit between {a} and {b} on that date."
            )
            return self._fact("ptp", f"{c1}-{c2}", f"edit {c1} / {c2} (deleted)", text, [])
        text = (
            f"The Medicare NCCI practitioner PTP edit file ({self.version}) contains no edit between codes "
            f"{a} and {b}, in either order, active or deleted."
        )
        return self._fact("ptp", f"{a}-{b}.none", f"no edit {a} / {b}", text, [])

    def mue_fact(self, code: str) -> Fact:
        row = self.mue(code)
        if row:
            _, value, adjudication, rationale = row
            text = (
                f"Medicare NCCI practitioner services MUE (effective {_date(self.mue_effective)}): code {code} has an "
                f"MUE value of {value} unit(s) of service. MUE adjudication indicator: {adjudication}. "
                f"MUE rationale: {rationale}."
            )
            return self._fact("mue", code, f"MUE {code}", text, [MUE_SECTION])
        text = f"The Medicare NCCI practitioner services MUE table (effective {_date(self.mue_effective)}) has no MUE value for code {code}."
        return self._fact("mue", f"{code}.none", f"no MUE {code}", text, [MUE_SECTION])

    def neighbour_fact(self, code: str, dos: int) -> Fact:
        n = self.neighbours(code, dos)

        def why(rows):
            return "; ".join(f"{r} ({c:,})" for r, c in rows) or "none"

        text = (
            f"Medicare NCCI PTP edits (practitioner, {self.version}), active on {_date(dos)}: code {code} is the "
            f"Column One code in {n['col1']:,} edits and the Column Two code in {n['col2']:,} edits. "
            f"As Column One, the most common rationales are: {why(n['col1_rationales'])}; examples of Column Two codes: "
            f"{', '.join(n['col1_examples']) or 'none'}. As Column Two, the most common rationales are: "
            f"{why(n['col2_rationales'])}; examples of Column One codes: {', '.join(n['col2_examples']) or 'none'}."
        )
        linked = [RATIONALE_SECTIONS.get(r.lower(), "") for r, _ in n["col1_rationales"] + n["col2_rationales"]]
        return self._fact("ptp", f"{code}.summary", f"edits for {code}", text, [s for s in linked if s][:3])

    def lookup(self, question: str, codes: list[str], date_of_service: int | None = None) -> list[Fact]:
        """Facts for the codes a question names. Rules, kept deliberately simple:
        * 2+ codes  -> the PTP edit (or its absence) for each pair of the first 4 codes;
        * 1 code + a PTP word ("bundled", "edit", "together") -> its one-hop edit summary;
        * MUE words ("MUE", "units", "how many") -> the MUE row for each of the first 3 codes."""
        dos = date_of_service or self.effective
        facts: list[Fact] = []
        if len(codes) >= 2:
            facts += [self.pair_fact(a, b, dos) for a, b in combinations(codes[:4], 2)]
        elif len(codes) == 1 and PTP_INTENT.search(question):
            facts.append(self.neighbour_fact(codes[0], dos))
        if codes and MUE_INTENT.search(question):
            facts += [self.mue_fact(c) for c in codes[:3]]
        return facts
