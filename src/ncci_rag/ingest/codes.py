"""Find HCPCS/CPT codes, code ranges, and modifiers in text.

Coding questions often hinge on an exact identifier ("Can 64450 be billed with
modifier 59?"). Embeddings are poor at exact identifiers, so we extract them at
ingestion into a small code index (code -> chunks that mention it) and use it as a
third retriever. This is also the seed of a knowledge graph: codes and modifiers are
entities, chunks and chapters are where they are governed.
"""

from __future__ import annotations

import re

# CPT Category I: 5 digits. Category II/III and PLA: 4 digits + F/T/U. HCPCS Level II: letter + 4 digits.
_CODE = r"(?:\d{5}|\d{4}[FTU]|[A-V]\d{4})"
CODE_RE = re.compile(rf"(?<![\w./-]){_CODE}(?![\w/])")
RANGE_RE = re.compile(rf"(?<![\w./-])({_CODE})\s*[-–]\s*({_CODE})(?![\w/])")

# "modifier 59", "modifiers 25, 58, 59, XE, XP, XS, and XU", "modifier -59".
# The word "modifier" may be any case; the modifier tokens themselves must be digits or
# capitals, so ordinary words after "modifier" ("is", "to", "and") are never captured.
_MOD = r"-?[0-9A-Z]{2}(?![0-9A-Za-z])"
_SEP = r"\s*(?:,\s*(?:and|or)\s+|,|/|\s+and\s+|\s+or\s+)\s*"
MODIFIER_LIST_RE = re.compile(rf"\b[Mm]odifiers?\s+({_MOD}(?:{_SEP}{_MOD})*)")
MODIFIER_BEFORE_RE = re.compile(r"(?<![0-9A-Za-z])([0-9A-Z]{2})\s+[Mm]odifiers?\b")  # "59 modifier"
_TOKEN_RE = re.compile(r"(?<![0-9A-Za-z])-?([0-9A-Z]{2})(?![0-9A-Za-z])")


def find_codes(text: str) -> list[str]:
    """Distinct codes in order of first appearance."""
    seen: dict[str, None] = {}
    for m in CODE_RE.finditer(text):
        seen.setdefault(m.group(0).upper(), None)
    return list(seen)


def find_ranges(text: str) -> list[tuple[str, str]]:
    return [(a.upper(), b.upper()) for a, b in RANGE_RE.findall(text)]


def find_modifiers(text: str) -> list[str]:
    seen: dict[str, None] = {}
    for m in MODIFIER_LIST_RE.finditer(text):
        for tok in _TOKEN_RE.findall(m.group(1)):
            seen.setdefault(tok, None)
    for m in MODIFIER_BEFORE_RE.finditer(text):
        seen.setdefault(m.group(1).upper(), None)
    return list(seen)


def code_sort_key(code: str) -> tuple[int, str]:
    """Comparable key so ranges like 20000-29999 or A0000-V9999 can be tested."""
    return (0 if code[0].isdigit() else 1, code)


def in_range(code: str, start: str, end: str) -> bool:
    """True if ``code`` lies within ``start``-``end`` of the same code family."""
    same_family = (code[0].isdigit() == start[0].isdigit()) and (code[-1].isalpha() == start[-1].isalpha())
    return same_family and len(code) == len(start) and code_sort_key(start) <= code_sort_key(code) <= code_sort_key(end)


def chapter_for_code(code: str, chapter_ranges: dict[str, tuple[str, str]]) -> str | None:
    """Which chapter governs a code, from the ranges each chapter declares in its title
    (e.g. Chapter IV: "CPT Codes 20000 - 29999")."""
    for chapter_id, (start, end) in chapter_ranges.items():
        if in_range(code.upper(), start, end):
            return chapter_id
    return None
