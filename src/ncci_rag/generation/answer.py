"""Grounded answer generation with claim-level citations.

Citation design: the model never writes a page number or a section name. It sees the
retrieved passages labelled S1..Sk and must return its answer as a list of sentences.
Each sentence carries the IDs of the passages that support it and one or more short
**verbatim quotes** from those passages (structured output, JSON schema).

The code then checks every sentence before it is shown:

1. **Source check.** Drop any ID the model invented (not one of the passages it was
   shown). A sentence with no valid source is removed.
2. **Quote check.** Every quote must appear, after whitespace/punctuation
   normalisation, in one of the passages the sentence cites. This catches support the
   model paraphrased into existence.
3. **Code anchoring.** Every HCPCS/CPT code named in the sentence must appear, literally
   or inside a stated range ("64400-64530"), in its quotes or in the source paragraph
   each quote comes from. The manual writes one rule per paragraph or list item, so the
   paragraph is the right scope: wide enough for "CPT codes 64400-64530 ... may be
   reported" to support a claim about 64450, narrow enough to reject a value borrowed
   from the next list item. This catches
   the most damaging coding error: a rule or value stated for one code being attributed
   to another code from the same passage. A real example from development:
   "The MUE value for CPT 64450 is one" was supported by a passage that says "The MUEs
   for these codes are one" about trichiasis codes 67820-67835. The chunk citation was
   valid; the claim was not.

Citations (chapter, section, printed page, PDF page) are built from chunk metadata,
so a citation can be missing, but it can never point to a place that does not exist.

Known limits (see docs/DESIGN.md): the checks are lexical. They cannot tell that a
quote is from the right *part* of a passage for a claim with no code in it, and they
cannot judge paraphrase quality. An entailment check (NLI model or LLM judge) per
sentence is the next step; these deterministic checks are the cheap first layer.
"""

from __future__ import annotations

import json
import re

from ..ingest.codes import find_codes, find_ranges, in_range
from ..models import Answer, AnswerSentence, Citation, RejectedSentence, ScoredChunk

SYSTEM_PROMPT = """You answer questions about the CMS 2026 Medicare NCCI Policy Manual for Medicare Services, and, when provided, the CMS Medicare NCCI edit tables.

Rules:
- Use ONLY the numbered source passages provided. Do not use outside knowledge, even if you know the answer.
- For every sentence, first copy one or more short quotes (a phrase or sentence, copied exactly) from the passages that directly support it, then list the IDs of those passages (e.g. ["S2"]), then write the sentence.
- Name a specific HCPCS/CPT code in a sentence only if your quotes for that sentence contain that code or a code range that includes it. If the manual states a general rule but does not name the asked-about code, state the general rule and say the manual does not name that code.
- A rule or value that a passage states for one code or code range must never be attributed to a different code.
- Sources labelled F are exact rows from the CMS Medicare NCCI edit tables (PTP code-pair edits, MUE values). Sources labelled S are passages of the policy manual. For a question about specific codes, state the fact from the F source (edit, modifier indicator, MUE value, or that there is no edit), then explain the policy behind it from the S sources. A "no edit" fact means the practitioner edit file has no edit for that pair; say so, and do not conclude that the codes are always payable together.
- The manual explains policy. Most MUE unit values, the PTP code-pair edits, and their modifier indicators are published in separate CMS data files, not in the manual. Give such a value only if an F source or a passage states it for that exact code; otherwise say it is not listed, and give the related policy the passages state.
- Quote codes, modifiers, and numeric values exactly as written in the sources.
- If the passages do not contain the answer, set "answerable" to false and explain briefly in "reason" what is missing. Do not guess.
- If the passages answer only part of the question, answer that part, and put what the manual does not address in "not_covered" (one short sentence, no citation). Leave "not_covered" empty when nothing is missing. Do not put "the manual does not say..." statements in "sentences".
- Be concise and precise, in plain language a medical coder would use. Prefer 2-6 sentences.
- The manual describes coding policy; it is not legal or billing advice for a specific claim. Do not give claim-specific advice beyond what the passages state."""

# Property order matters for generation: the model writes the quotes before the
# sentence, so the sentence is written from the evidence rather than justified after.
ANSWER_SCHEMA = {
    "name": "grounded_answer",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "answerable": {"type": "boolean"},
            "sentences": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "quotes": {"type": "array", "items": {"type": "string"}},
                        "source_ids": {"type": "array", "items": {"type": "string"}},
                        "text": {"type": "string"},
                    },
                    "required": ["quotes", "source_ids", "text"],
                },
            },
            "not_covered": {"type": "string"},
            "reason": {"type": "string"},
        },
        "required": ["answerable", "sentences", "not_covered", "reason"],
    },
}

_QUOTE_CHARS = str.maketrans({"“": '"', "”": '"', "‘": "'", "’": "'", "–": "-", "—": "-", " ": " "})
_ELLIPSIS_RE = re.compile(r"\s*(?:\.\.\.|…)\s*")


def normalise(text: str) -> str:
    """Lowercase, unify quote/dash characters, collapse whitespace."""
    return re.sub(r"\s+", " ", text.translate(_QUOTE_CHARS).lower()).strip()


def _parts(quote: str) -> list[str]:
    parts = [normalise(p).strip(" .,;:\"'") for p in _ELLIPSIS_RE.split(quote)]
    return [p for p in parts if p]


def quote_found(quote: str, sources: list[str]) -> bool:
    """True if every part of ``quote`` (split at ellipses) appears in one of ``sources``."""
    parts = _parts(quote)
    return bool(parts) and any(all(p in normalise(src) for p in parts) for src in sources)


def quote_paragraphs(quotes: list[str], sources: list[str]) -> list[str]:
    """The source paragraphs (chunk text is paragraphs joined by blank lines) that
    contain any part of any quote: the context a claim's codes may come from."""
    parts = [p for q in quotes for p in _parts(q)]
    return [para for src in sources for para in src.split("\n\n") if any(p in normalise(para) for p in parts)]


def unanchored_codes(sentence: str, quotes: list[str], context: list[str] | None = None) -> list[str]:
    """Codes named in ``sentence`` that neither its quotes nor their source paragraphs
    contain or cover by a range."""
    anchor = " ".join(quotes + (context or []))
    codes_present = set(find_codes(anchor))
    ranges = find_ranges(anchor)
    return [
        code
        for code in find_codes(sentence)
        if code not in codes_present and not any(in_range(code, a, b) for a, b in ranges)
    ]


def format_sources(passages: list[ScoredChunk]) -> tuple[str, dict[str, ScoredChunk]]:
    """Label facts from the edit tables F1..Fn and manual passages S1..Sn."""
    by_id: dict[str, ScoredChunk] = {}
    blocks = []
    n_fact = n_manual = 0
    for p in passages:
        c = p.chunk
        if c.is_fact:
            n_fact += 1
            sid = f"F{n_fact}"
        else:
            n_manual += 1
            sid = f"S{n_manual}"
        by_id[sid] = p
        blocks.append(f"[{sid}] {c.heading}, {c.pages}\n{c.text}")
    return "\n\n---\n\n".join(blocks), by_id


def check_sentence(text: str, source_ids: list[str], quotes: list[str], by_id: dict[str, ScoredChunk]) -> str | None:
    """Return why a sentence fails grounding, or None if it passes."""
    if not source_ids:
        return "no valid source"
    if not quotes:
        return "no supporting quote"
    cited = [by_id[sid].chunk.text for sid in source_ids]
    missing = [q for q in quotes if not quote_found(q, cited)]
    if missing:
        return f"quote not found in cited source: {missing[0][:80]!r}"
    loose = unanchored_codes(text, quotes, quote_paragraphs(quotes, cited))
    if loose:
        return f"code {', '.join(loose)} not in the quoted paragraph"
    return None


def parse_and_validate(question: str, raw: dict, by_id: dict[str, ScoredChunk], passages: list[ScoredChunk]) -> Answer:
    """Turn the model's JSON into an Answer, keeping only sentences that pass every check."""
    sentences: list[AnswerSentence] = []
    rejected: list[RejectedSentence] = []
    for s in raw.get("sentences", []):
        text = (s.get("text") or "").strip()
        if not text:
            continue
        valid = [sid for sid in dict.fromkeys(s.get("source_ids", [])) if sid in by_id]
        quotes = [q.strip() for q in s.get("quotes", []) if q and q.strip()]
        problem = check_sentence(text, valid, quotes, by_id)
        if problem:
            rejected.append(RejectedSentence(text, problem))  # unsupported claims are not shown
        else:
            sentences.append(AnswerSentence(text, valid, quotes))

    answerable = bool(raw.get("answerable")) and bool(sentences)
    citations: list[Citation] = []
    if answerable:
        for s in sentences:
            for sid in s.source_ids:
                if sid not in {c.source_id for c in citations}:
                    citations.append(Citation(sid, by_id[sid].chunk))
    reason = raw.get("reason", "") if not answerable else ""
    if not answerable and not reason:
        reason = "The retrieved sections of the manual do not answer this question."
        if rejected:
            reason += " (A draft answer was withheld because its claims could not be matched to the cited text.)"
    not_covered = (raw.get("not_covered") or "").strip() if answerable else ""
    return Answer(question, answerable, sentences if answerable else [], citations, passages, reason, rejected, not_covered)


def generate_answer(question: str, passages: list[ScoredChunk], model: str, client) -> Answer:
    sources, by_id = format_sources(passages)
    resp = client.chat.completions.create(
        model=model,
        temperature=0,
        response_format={"type": "json_schema", "json_schema": ANSWER_SCHEMA},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Question: {question}\n\nSource passages:\n\n{sources}"},
        ],
    )
    raw = json.loads(resp.choices[0].message.content or "{}")
    return parse_and_validate(question, raw, by_id, passages)
