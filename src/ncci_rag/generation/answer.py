"""Grounded answer generation with claim-level citations.

Citation design: the model never writes a page number or a section name. It sees the
retrieved passages labelled S1..Sk and must return its answer as a list of sentences,
each with the IDs of the passages that support it (structured output, JSON schema).
The code then:
* drops any ID the model invents (not one of the passages it was shown),
* drops a sentence that ends up with no valid support,
* builds citations (chapter, section, printed page, PDF page) from the chunk metadata.

So a citation can be missing, but it can never point to a place that does not exist
or that the model was not shown.
"""

from __future__ import annotations

import json

from ..models import Answer, AnswerSentence, Citation, ScoredChunk

SYSTEM_PROMPT = """You answer questions about the CMS 2026 Medicare NCCI Policy Manual for Medicare Services.

Rules:
- Use ONLY the numbered source passages provided. Do not use outside knowledge, even if you know the answer.
- Every sentence in your answer must list the IDs of the passages that support it (e.g. ["S2"]). Cite only passages that actually contain the information.
- Quote HCPCS/CPT codes, modifiers, and numeric values exactly as written in the sources.
- If the passages do not contain the answer, set "answerable" to false and explain briefly in "reason" what is missing. Do not guess.
- If the passages answer only part of the question, answer that part and say what the manual does not address.
- Be concise and precise, in plain language a medical coder would use. Prefer 2-6 sentences.
- The manual describes coding policy; it is not legal or billing advice for a specific claim. Do not give claim-specific advice beyond what the passages state."""

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
                        "text": {"type": "string"},
                        "source_ids": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["text", "source_ids"],
                },
            },
            "reason": {"type": "string"},
        },
        "required": ["answerable", "sentences", "reason"],
    },
}


def format_sources(passages: list[ScoredChunk]) -> tuple[str, dict[str, ScoredChunk]]:
    by_id: dict[str, ScoredChunk] = {}
    blocks = []
    for i, p in enumerate(passages, start=1):
        sid = f"S{i}"
        by_id[sid] = p
        c = p.chunk
        blocks.append(f"[{sid}] {c.heading}, {c.pages}\n{c.text}")
    return "\n\n---\n\n".join(blocks), by_id


def parse_and_validate(question: str, raw: dict, by_id: dict[str, ScoredChunk], passages: list[ScoredChunk]) -> Answer:
    """Turn the model's JSON into an Answer, enforcing that every claim is supported."""
    sentences: list[AnswerSentence] = []
    for s in raw.get("sentences", []):
        valid = [sid for sid in dict.fromkeys(s.get("source_ids", [])) if sid in by_id]
        text = (s.get("text") or "").strip()
        if text and valid:
            sentences.append(AnswerSentence(text, valid))
        # A sentence with no valid source is dropped: unsupported claims are not shown.

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
    return Answer(question, answerable, sentences if answerable else [], citations, passages, reason)


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
