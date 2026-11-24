"""Turn parsed sections into retrieval chunks.

Rules, in order of priority:
1. A chunk never crosses a section boundary. Sections are the unit a coder cites
   ("Chapter I, Section E"), so a chunk that mixes two sections makes citations vague.
2. Paragraphs are packed into chunks of roughly ``target_words`` words. Policy text
   is dense; ~250 words (~330 tokens) keeps one rule and its exceptions together while
   staying specific enough to rank well.
3. Prefer to start a new chunk where a list item starts ("b. Modifier 25: ..."), so an
   item and its explanation stay together.
4. A single paragraph longer than ``max_words`` is split at sentence boundaries.
"""

from __future__ import annotations

import re

from ..models import Chunk, Paragraph, Section
from .codes import find_codes, find_modifiers

LIST_ITEM_RE = re.compile(r"^(\d{1,2}|[a-z]|[ivx]{1,4})\.\s")
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.;:])\s+(?=[A-Z(“\"])")


def _words(text: str) -> int:
    return len(text.split())


def _split_long(p: Paragraph, max_words: int) -> list[Paragraph]:
    if _words(p.text) <= max_words:
        return [p]
    parts, buf = [], ""
    for sent in SENTENCE_SPLIT_RE.split(p.text):
        if buf and _words(buf) + _words(sent) > max_words:
            parts.append(Paragraph(buf.strip(), p.page, p.page_label))
            buf = ""
        buf += " " + sent
    if buf.strip():
        parts.append(Paragraph(buf.strip(), p.page, p.page_label))
    return parts


def chunk_sections(
    sections: list[Section],
    target_words: int = 250,
    max_words: int = 400,
    min_words_before_item_break: int = 120,
) -> list[Chunk]:
    chunks: list[Chunk] = []
    for sec in sections:
        paras = [q for p in sec.paragraphs for q in _split_long(p, max_words)]
        groups: list[list[Paragraph]] = []
        cur: list[Paragraph] = []
        cur_words = 0
        for p in paras:
            n = _words(p.text)
            starts_item = bool(LIST_ITEM_RE.match(p.text))
            full = cur_words + n > target_words and cur_words > 0
            item_break = starts_item and cur_words >= min_words_before_item_break
            if cur and (full or item_break):
                groups.append(cur)
                cur, cur_words = [], 0
            cur.append(p)
            cur_words += n
        if cur:
            # Avoid a tiny trailing chunk: merge it into the previous one if that stays reasonable.
            if groups and cur_words < 60 and _words(" ".join(x.text for x in groups[-1])) + cur_words <= max_words:
                groups[-1].extend(cur)
            else:
                groups.append(cur)

        for i, g in enumerate(groups, start=1):
            text = "\n\n".join(p.text for p in g)
            chunks.append(
                Chunk(
                    chunk_id=f"{sec.chapter_id}.{sec.section_id[:24]}.{i:02d}",
                    chapter_id=sec.chapter_id,
                    chapter_title=sec.chapter_title,
                    code_range=sec.code_range,
                    section_id=sec.section_id,
                    section_title=sec.section_title,
                    page_start=g[0].page,
                    page_end=g[-1].page,
                    label_start=g[0].page_label,
                    label_end=g[-1].page_label,
                    text=text,
                    codes=find_codes(text),
                    modifiers=find_modifiers(text),
                )
            )
    return chunks
