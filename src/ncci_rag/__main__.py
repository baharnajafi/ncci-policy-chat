"""Command-line interface.

    python -m ncci_rag ingest                 # parse the PDF, embed, build data/index.sqlite
    python -m ncci_rag load-edits             # load CMS PTP/MUE zips from data/edits into data/edits.sqlite
    python -m ncci_rag ask "When is modifier 59 appropriate?"
    python -m ncci_rag ask --debug "..."      # also show retrieval scores
    python -m ncci_rag chat                   # interactive loop
"""

from __future__ import annotations

import argparse
import sys

from .config import get_settings


def _print_answer(answer, result, debug: bool) -> None:
    print()
    print(answer.text)
    if answer.citations:
        print("\nSources:")
        for i, c in enumerate(answer.citations, start=1):
            print(f"  [{i}] {c.chunk.heading}, {c.chunk.pages}")
    if debug and answer.rejected:
        print("\nRemoved by the claim check:")
        for r in answer.rejected:
            print(f"  - {r.text}  ({r.reason})")
    if debug:
        print(f"\nretrieval: top relevance={result.top_relevance:.3f} gate={'pass' if result.passed_gate else 'FAIL'} "
              f"codes={result.query_codes} modifiers={result.query_modifiers} routed_chapter={result.routed_chapter}")
        for f in result.facts:
            print(f"  fact {f.chunk.chunk_id:28} -> linked sections {f.linked_sections}")
        for p in result.passages:
            print(f"  {p.score:.3f}  {p.chunk.chunk_id:16} {p.chunk.pages:34} ranks={p.ranks}")
    print()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ncci_rag")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("ingest", help="parse the PDF and build the index")
    sub.add_parser("load-edits", help="load the CMS PTP and MUE edit files")
    ask = sub.add_parser("ask", help="answer one question")
    ask.add_argument("question")
    ask.add_argument("--chapter", help="restrict to a chapter, e.g. I or XI")
    ask.add_argument("--debug", action="store_true")
    chat = sub.add_parser("chat", help="interactive question loop")
    chat.add_argument("--debug", action="store_true")
    args = parser.parse_args(argv)

    if args.cmd == "ingest":
        from .pipeline import build_index

        build_index(get_settings())
        return 0
    if args.cmd == "load-edits":
        from .edits.loader import load_edits

        s = get_settings()
        load_edits(s.edits_dir, s.edits_db)
        return 0

    from .pipeline import QAPipeline

    qa = QAPipeline(get_settings())
    if args.cmd == "ask":
        _print_answer(*qa.ask(args.question, args.chapter), debug=args.debug)
        return 0

    print("Ask about the 2026 Medicare NCCI Policy Manual. Empty line to quit.")
    while True:
        try:
            q = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not q:
            break
        _print_answer(*qa.ask(q), debug=args.debug)
    return 0


if __name__ == "__main__":
    sys.exit(main())
