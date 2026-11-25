"""Evaluate retrieval (and optionally answers) on a small labelled question set.

    python eval/run_eval.py                 # retrieval metrics + relevance-gate calibration
    python eval/run_eval.py --answers       # also generate answers and grade them

Question types in eval/questions.jsonl:

* **Positive** questions list the sections that answer them ("I.E" = Chapter I,
  Section E). They measure retrieval (hit@k, MRR) and, with --answers, whether the
  answer cites a correct section.
* **Negative** questions are clearly outside the manual (Part B premium, a portal
  password). They set the noise floor for the relevance gate.
* **Fact** questions need the CMS edit tables (an MUE value, a PTP pair, a deleted
  edit, a code's edit summary). Each names the fact that should be looked up and
  regexes the answer must (and must not) match. Skipped if the tables are not loaded.
* **Hard negatives** are in-domain questions neither the manual nor the edit tables
  answer: a fee schedule amount, an OPPS rate, ICD-10 codes, Medicaid policy. They look like coding
  questions, so retrieval finds relevant-looking passages and the gate usually lets
  them through. They test the *answer* layer: the model must abstain, or answer only
  the related policy without inventing the value. Each one has either
  ``expect_abstain`` or ``must_not_match`` regexes for the fabricated value.

The report shows:

* hit@1/3/k and MRR, plus the rank each individual retriever (keyword, vector, code)
  gave the first relevant chunk, so you can see what each one adds;
* the top relevance score for every question, and a threshold sweep over positives and
  (easy) negatives; hard negatives are shown separately, because no retrieval threshold
  can separate them;
* with --answers: how many sentences the claim check removed, whether each positive
  cites an expected section, and whether each hard negative stayed clean.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ncci_rag.config import get_settings  # noqa: E402
from ncci_rag.pipeline import QAPipeline  # noqa: E402


def section_of(chunk_id: str) -> str:
    return chunk_id.rsplit(".", 1)[0]


def is_relevant(chunk_id: str, expected: list[str]) -> bool:
    sec = section_of(chunk_id)
    return any(sec == e or sec.startswith(e) for e in expected)


def kind_of(item: dict) -> str:
    if item.get("fact"):
        return "fact"
    if item.get("hard_negative"):
        return "hard"
    return "negative" if item.get("negative") else "positive"


def hard_negative_clean(item: dict, answer) -> bool:
    """A hard negative is handled correctly if the system abstains, or answers without
    stating the value the manual does not contain."""
    if not answer.answerable:
        return True
    if item.get("expect_abstain"):
        return False
    return not any(re.search(p, answer.text, re.I) for p in item.get("must_not_match", []))


def fact_correct(item: dict, answer) -> bool:
    text = answer.text
    return (answer.answerable
            and all(re.search(p, text, re.I) for p in item.get("must_match", []))
            and not any(re.search(p, text, re.I) for p in item.get("must_not_match", [])))


CALIBRATION_GRID = [0.01, 0.02, 0.05, 0.10, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90]


def gate_threshold(settings) -> float:
    """The threshold the gate actually uses: reranker score, or dense cosine without a reranker."""
    return settings.min_relevance if settings.use_reranker else settings.min_dense_similarity


def calibration_table(pos: list[float], neg: list[float], hard: list[float], current: float) -> list[str]:
    """Error rates of the relevance gate at each threshold.

    * wrong refusal: an in-scope question gets "not in the manual" (positives below t);
    * wrong pass: an out-of-scope question reaches the LLM (easy negatives at or above t);
    * hard negatives passed: in-domain questions the manual cannot answer that reach the
      answer layer. This is expected and is not counted as a gate error: the gate judges
      topic relevance, and the claim check and `answerable` handle missing facts.

    The scores are not calibrated probabilities (a sigmoid over cross-encoder logits keeps
    order, not meaning), so the threshold is chosen from these empirical rates."""

    def pct(k: int, n: int) -> str:
        return f"{k}/{n} ({100 * k / n:.0f}%)" if n else "-"

    out = ["", f"Current threshold: **{current}** (row in bold).", "",
           "| threshold | wrong refusals (positives blocked) | wrong passes (negatives reaching the LLM) | hard negatives passed to the answer layer |",
           "|---|---|---|---|"]
    for t in sorted(set(CALIBRATION_GRID) | {current}):
        row = (f"| {t:.2f} | {pct(sum(s < t for s in pos), len(pos))} | {pct(sum(s >= t for s in neg), len(neg))} "
               f"| {pct(sum(s >= t for s in hard), len(hard))} |")
        out.append(row.replace(f"| {t:.2f} |", f"| **{t:.2f}** |", 1) if t == current else row)
    safe = [t for t in CALIBRATION_GRID if all(s >= t for s in pos) and all(s < t for s in neg)]
    if safe:
        out += ["", f"Thresholds with no gate error on this set: {safe[0]:.2f} to {safe[-1]:.2f}. A low value in that "
                "range favours answering (a wrong 'not found' is costly for a coder); later layers catch weak answers."]
    return out


def md(text: str) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--questions", default=str(ROOT / "eval" / "questions.jsonl"))
    ap.add_argument("--answers", action="store_true", help="also generate answers (costs a few cents)")
    ap.add_argument("--report", default=str(ROOT / "eval" / "report.md"))
    args = ap.parse_args()

    settings = get_settings()
    qa = QAPipeline(settings)
    items = [json.loads(line) for line in Path(args.questions).read_text().splitlines() if line.strip()]

    if qa.edits is None:
        print("Edit tables not loaded (python -m ncci_rag load-edits): skipping fact questions.")
        items = [it for it in items if not it.get("fact")]
    rows = []
    scores: dict[str, list[float]] = {"positive": [], "negative": [], "hard": [], "fact": []}
    hits1 = hits3 = hitsk = 0
    mrr = 0.0
    for it in items:
        kind = kind_of(it)
        res = qa.retrieve(it["question"])
        scores[kind].append(res.top_relevance)
        row = {"id": it["id"], "question": it["question"], "kind": kind,
               "top_relevance": round(res.top_relevance, 3), "gate": res.passed_gate}
        if kind == "positive":
            ranks = [i for i, p in enumerate(res.passages, start=1) if is_relevant(p.chunk.chunk_id, it["expected"])]
            first = ranks[0] if ranks else None
            hits1 += first == 1
            hits3 += bool(first and first <= 3)
            hitsk += bool(first)
            mrr += 1 / first if first else 0
            row["first_relevant_rank"] = first
            # Rank of the first relevant chunk in each retriever, before fusion. Only
            # chunks that reached the final top-k are visible here, so "None" means
            # "did not contribute a relevant chunk to the final list".
            for name in ("keyword", "vector", "code"):
                r = [p.ranks.get(name) for p in res.passages if is_relevant(p.chunk.chunk_id, it["expected"]) and p.ranks.get(name)]
                row[f"{name}_rank"] = min(r) if r else None
        if kind == "fact":
            row["fact_found"] = it["fact"] in [f.chunk.chunk_id for f in res.facts]
            row["linked_in_passages"] = bool(it["expected"]) and any(
                is_relevant(p.chunk.chunk_id, it["expected"]) for p in res.passages)
        if args.answers and (kind != "negative" or res.passed_gate):
            answer, _ = qa.ask(it["question"])
            row["answerable"] = answer.answerable
            row["rejected"] = [f"{r.text} ({r.reason})" for r in answer.rejected]
            row["answer"] = answer.text
            if kind == "positive":
                row["cited_expected"] = any(is_relevant(c.chunk.chunk_id, it["expected"]) for c in answer.citations)
            if kind == "hard":
                row["clean"] = hard_negative_clean(it, answer)
            if kind == "fact":
                row["fact_cited"] = it["fact"] in [c.chunk.chunk_id for c in answer.citations]
                row["manual_cited"] = any(not c.chunk.is_fact for c in answer.citations)
                row["correct"] = fact_correct(it, answer)
        rows.append(row)

    pos, neg, hard = scores["positive"], scores["negative"], scores["hard"]
    n_pos, k = len(pos), settings.top_k
    lines = [
        "# Evaluation report",
        "",
        f"Settings: embed={settings.embed_model}, reranker={settings.reranker_model}, chat={settings.chat_model}, "
        f"top_k={k}, min_relevance={settings.min_relevance}",
        "",
        f"**Retrieval ({n_pos} questions):** hit@1 {hits1}/{n_pos} · hit@3 {hits3}/{n_pos} · hit@{k} {hitsk}/{n_pos} · MRR {mrr / max(n_pos, 1):.2f}",
        "",
        "| id | first relevant rank | keyword | vector | code | top relevance | gate | question |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        gate = "pass" if r["gate"] else "blocked"
        if r["kind"] == "positive":
            lines.append(
                f"| {r['id']} | {r['first_relevant_rank']} | {r['keyword_rank']} | {r['vector_rank']} | {r['code_rank']} | "
                f"{r['top_relevance']} | {gate if r['gate'] else 'BLOCKED'} | {md(r['question'])} |"
            )
        elif r["kind"] == "fact":
            lines.append(f"| {r['id']} | (fact: {'found' if r['fact_found'] else 'NOT FOUND'}) | | | | {r['top_relevance']} | {gate} | {md(r['question'])} |")
        else:
            label = "(negative)" if r["kind"] == "negative" else "(hard negative)"
            lines.append(f"| {r['id']} | {label} | | | | {r['top_relevance']} | {gate} | {md(r['question'])} |")

    # Threshold sweep for the relevance gate: positives vs. easy negatives.
    lines += ["", "## Relevance gate calibration", ""]
    if pos and neg:
        lo, hi = max(neg), min(pos)
        lines.append(f"Lowest positive top score: {hi:.3f}. Highest negative top score: {lo:.3f}.")
        if hi > lo:
            lines.append(f"Separable: any threshold between them works; midpoint = **{(hi + lo) / 2:.3f}** "
                         f"(set NCCI_MIN_RELEVANCE, or NCCI_MIN_DENSE_SIM without a reranker).")
        else:
            lines.append("Not separable on this set: choose the threshold by the cost of each error "
                         "(a wrong 'not found' vs. an answer built on irrelevant text).")
        lines += calibration_table(pos, neg, hard, gate_threshold(settings))
    if hard:
        t = gate_threshold(settings)
        passed = sum(s >= t for s in hard)
        lines += ["", f"Hard negatives passing the gate at {t}: **{passed}/{len(hard)}** "
                  f"(top scores {', '.join(f'{s:.2f}' for s in sorted(hard))}). These are in-domain, so retrieval "
                  "correctly finds related policy; the answer layer must handle them."]

    fact_rows = [r for r in rows if r["kind"] == "fact"]
    if fact_rows:
        lines += ["", f"**Edit-table facts:** looked up {sum(r['fact_found'] for r in fact_rows)}/{len(fact_rows)}; "
                  f"linked manual section in the passages {sum(r['linked_in_passages'] for r in fact_rows)}/"
                  f"{sum(1 for it in items if it.get('fact') and it['expected'])} (questions with an expected section)"]

    if args.answers:
        answered = [r for r in rows if "answer" in r]
        pos_rows = [r for r in answered if r["kind"] == "positive"]
        hard_rows = [r for r in answered if r["kind"] == "hard"]
        n_rej = sum(len(r["rejected"]) for r in answered)
        lines += [
            "", "## Answers", "",
            f"- Positives answered: {sum(r['answerable'] for r in pos_rows)}/{len(pos_rows)}; "
            f"citing an expected section: {sum(r['cited_expected'] for r in pos_rows)}/{len(pos_rows)}",
            *([f"- Fact questions answered correctly: **{sum(r['correct'] for r in answered if r['kind'] == 'fact')}/{len([r for r in answered if r['kind'] == 'fact'])}**; "
               f"citing the table row: {sum(r['fact_cited'] for r in answered if r['kind'] == 'fact')}; "
               f"also citing the manual (the why): {sum(r['manual_cited'] for r in answered if r['kind'] == 'fact')}"]
              if any(r["kind"] == "fact" for r in answered) else []),
            f"- Hard negatives handled cleanly (abstained, or no invented value): "
            f"**{sum(r['clean'] for r in hard_rows)}/{len(hard_rows)}**",
            f"- Sentences removed by the claim check: {n_rej} "
            f"(in {sum(bool(r['rejected']) for r in pos_rows)} positive and "
            f"{sum(bool(r['rejected']) for r in hard_rows)} hard-negative answers)",
            "",
        ]
        for r in answered:
            tags = [f"answerable={r['answerable']}"]
            if "cited_expected" in r:
                tags.append(f"cited_expected={r['cited_expected']}")
            if "clean" in r:
                tags.append(f"clean={r['clean']}")
            if "correct" in r:
                tags.append(f"correct={r['correct']} fact_cited={r['fact_cited']} manual_cited={r['manual_cited']}")
            lines.append(f"**{r['id']}** {r['question']}  \n{' '.join(tags)}  \n{r['answer']}")
            for rej in r["rejected"]:
                lines.append(f"  \n_removed:_ {rej}")
            lines.append("")

    Path(args.report).write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    print(f"\nFull report: {args.report}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
