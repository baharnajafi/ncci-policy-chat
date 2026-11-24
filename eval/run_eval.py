"""Evaluate retrieval (and optionally answers) on a small labelled question set.

    python eval/run_eval.py                 # retrieval metrics + relevance-gate calibration
    python eval/run_eval.py --answers       # also generate answers and check their citations

Each positive question lists the sections that answer it ("I.E" = Chapter I,
Section E). Negative questions are about things the manual does not cover; they set
the "noise floor" for the relevance gate. The report shows:

* hit@1/3/k and MRR for the final ranking, and the rank each individual retriever
  (keyword, vector, code) gave the first relevant chunk, so you can see what each adds;
* the top relevance score for every question, and a threshold sweep: the gate should
  block every negative question while letting every positive one through.
"""

from __future__ import annotations

import argparse
import json
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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--questions", default=str(ROOT / "eval" / "questions.jsonl"))
    ap.add_argument("--answers", action="store_true", help="also generate answers (costs a few cents)")
    ap.add_argument("--report", default=str(ROOT / "eval" / "report.md"))
    args = ap.parse_args()

    settings = get_settings()
    qa = QAPipeline(settings)
    items = [json.loads(line) for line in Path(args.questions).read_text().splitlines() if line.strip()]

    rows, pos_scores, neg_scores = [], [], []
    hits1 = hits3 = hitsk = 0
    mrr = 0.0
    for it in items:
        res = qa.retrieve(it["question"])
        neg = it.get("negative", False)
        (neg_scores if neg else pos_scores).append(res.top_relevance)
        row = {"id": it["id"], "question": it["question"], "negative": neg,
               "top_relevance": round(res.top_relevance, 3), "gate": res.passed_gate}
        if not neg:
            ranks = [i for i, p in enumerate(res.passages, start=1) if is_relevant(p.chunk.chunk_id, it["expected"])]
            first = ranks[0] if ranks else None
            hits1 += first == 1
            hits3 += bool(first and first <= 3)
            hitsk += bool(first)
            mrr += 1 / first if first else 0
            row["first_relevant_rank"] = first
            row["top_chunk"] = res.passages[0].chunk.chunk_id if res.passages else None
            # Rank of the first relevant chunk in each retriever, before fusion.
            for name in ("keyword", "vector", "code"):
                r = [p.ranks.get(name) for p in res.passages if is_relevant(p.chunk.chunk_id, it["expected"]) and p.ranks.get(name)]
                row[f"{name}_rank"] = min(r) if r else None
        if args.answers and (not neg or res.passed_gate):
            answer, _ = qa.ask(it["question"])
            row["answerable"] = answer.answerable
            row["cited_expected"] = any(is_relevant(c.chunk.chunk_id, it["expected"]) for c in answer.citations) if not neg else None
            row["answer"] = answer.text
        rows.append(row)

    n_pos = len(pos_scores)
    k = settings.top_k
    lines = [
        "# Evaluation report",
        "",
        f"Settings: embed={settings.embed_model}, reranker={settings.reranker_model}, chat={settings.chat_model}, top_k={k}",
        "",
        f"**Retrieval ({n_pos} questions):** hit@1 {hits1}/{n_pos} · hit@3 {hits3}/{n_pos} · hit@{k} {hitsk}/{n_pos} · MRR {mrr / max(n_pos, 1):.2f}",
        "",
        "| id | first relevant rank | keyword | vector | code | top relevance | gate | question |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        if r["negative"]:
            lines.append(f"| {r['id']} | (negative) | | | | {r['top_relevance']} | {'pass' if r['gate'] else 'blocked'} | {r['question']} |")
        else:
            lines.append(
                f"| {r['id']} | {r['first_relevant_rank']} | {r['keyword_rank']} | {r['vector_rank']} | {r['code_rank']} | "
                f"{r['top_relevance']} | {'pass' if r['gate'] else 'BLOCKED'} | {r['question']} |"
            )

    # Threshold sweep for the relevance gate.
    lines += ["", "## Relevance gate calibration", ""]
    if pos_scores and neg_scores:
        lo, hi = max(neg_scores), min(pos_scores)
        lines.append(f"Lowest positive top score: {hi:.3f}. Highest negative top score: {lo:.3f}.")
        if hi > lo:
            lines.append(f"Separable: any threshold between them works; midpoint = **{(hi + lo) / 2:.3f}** "
                         f"(set NCCI_MIN_RELEVANCE, or NCCI_MIN_DENSE_SIM without a reranker).")
        else:
            lines.append("Not separable on this set: choose the threshold by the cost of each error "
                         "(a wrong 'not found' vs. an answer built on irrelevant text).")
        lines += ["", "| threshold | positives passed | negatives blocked |", "|---|---|---|"]
        for t in sorted({round(x, 2) for x in pos_scores + neg_scores}):
            lines.append(f"| {t:.2f} | {sum(s >= t for s in pos_scores)}/{n_pos} | {sum(s < t for s in neg_scores)}/{len(neg_scores)} |")

    if args.answers:
        lines += ["", "## Answers", ""]
        for r in rows:
            if "answer" in r:
                lines.append(f"**{r['id']}** {r['question']}  \nanswerable={r['answerable']} cited_expected={r['cited_expected']}  \n{r['answer']}\n")

    Path(args.report).write_text("\n".join(lines) + "\n")
    print("\n".join(lines[:8 + len(rows)]))
    print(f"\nFull report: {args.report}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
