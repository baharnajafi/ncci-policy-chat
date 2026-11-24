"""Parse the NCCI Policy Manual PDF into chapters, sections, and paragraphs.

The manual has a regular layout, and the parser relies on it instead of generic
text splitting:

* Every chapter starts with a cover page and its own table of contents; real content
  begins at a bold, centred "Chapter IV" line, followed by the chapter title and,
  for most chapters, the code range it covers ("CPT Codes 20000 - 29999").
* Sections are bold lines at the left margin: "A. Introduction", "B. ...". The
  Introduction uses unlettered bold headings ("Purpose", ...).
* Every page ends with a footer: "Revision Date (Medicare): 1/1/2026" and the page
  number printed in the manual ("I-15"). We drop the footer from the text but keep
  the printed page number, because that is what a coder would look up.
* Paragraphs are separated by a larger vertical gap than lines within a paragraph.

Using layout signals (bold font, x-position, vertical gaps) keeps section boundaries
exact, which matters more for citation quality than any chunk-size setting.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import pdfplumber

from ..models import Paragraph, Section

LEFT_MARGIN = 72.0  # x position of body text and section headings (points)
FOOTER_TOP = 680.0  # lines below this are footer
PARAGRAPH_GAP = 1.5  # a gap larger than 1.5 x the normal line pitch starts a paragraph

CHAPTER_RE = re.compile(r"^Chapter\s+([IVXL]+)$")
SECTION_RE = re.compile(r"^([A-Z])\.\s*(\S.*)$")
CODE_RANGE_RE = re.compile(r"(CPT Codes|HCPCS Level II Codes)\s+\S+\s*[-–]\s*\S+", re.I)
PAGE_LABEL_RE = re.compile(r"^(Intro-\d+|[IVXL]+-\d+|[A-Za-z]+-\d+|Page \d+)$")
TOC_ENTRY_RE = re.compile(r"\s(Intro-\d+|[IVXL]+-\d+)$")
LIST_MARKER_RE =re.compile(r"^(\d{1,2}|[a-z]|[ivx]{1,4})\.\s*(?=\S)")
GLUED_MARKER_RE = re.compile(r"^((?:\d{1,2}|[a-zA-Z])\.)(?=[A-Z(“\"])")  # "a.Modifier" -> "a. Modifier"


@dataclass
class _Line:
    text: str
    x0: float
    top: float
    bold: bool
    page: int


def _is_bold(chars: list[dict]) -> bool:
    """A line is bold if (almost) all of its visible characters are; headings sometimes
    contain a single regular-weight character such as "&"."""
    visible = [c for c in chars if c["text"].strip()]
    if not visible:
        return False
    return sum("Bold" in c["fontname"] for c in visible) / len(visible) >= 0.8


def _page_lines(page, page_no: int) -> tuple[list[_Line], str]:
    """Return body lines of one page, and the printed page label from its footer."""
    lines, label = [], ""
    for ln in page.extract_text_lines(x_tolerance=1.5, return_chars=True):
        text = ln["text"].strip()
        if not text:
            continue
        if ln["top"] >= FOOTER_TOP:
            if PAGE_LABEL_RE.match(text):
                label = text
            continue  # footer: revision date and page number
        text = GLUED_MARKER_RE.sub(r"\1 ", text)
        lines.append(_Line(text, ln["x0"], ln["top"], _is_bold(ln["chars"]), page_no))
    return lines, label or str(page_no)


def _join(lines: list[str]) -> str:
    """Join wrapped lines; keep hyphenated compounds split across lines intact."""
    out = ""
    for ln in lines:
        if not out:
            out = ln
        elif out.endswith("-") and ln[:1].islower():
            out += ln  # "PTP-" + "associated" -> "PTP-associated"
        else:
            out += " " + ln
    return re.sub(r"\s+", " ", out).strip()


def parse_manual(pdf_path: str | Path) -> list[Section]:
    """Parse the manual into sections of paragraphs.

    The parser is a small state machine over pages:
    * ``chapter is None`` -> we are on a cover / table-of-contents page; skip text.
    * a bold "Chapter X" line -> start a chapter; the bold lines after it are its title.
    * a bold "A. Title" line at the left margin -> start a section.
    """
    sections: list[Section] = []
    chapter_id: str | None = None
    chapter_title_parts: list[str] = []
    code_range: str | None = None
    current: Section | None = None
    expected_letter = "A"

    para_lines: list[str] = []
    para_page, para_label = 0, ""
    last_top: float | None = None
    pitch = 13.8  # typical line pitch in this manual; refined as we read

    def flush_paragraph():
        nonlocal para_lines
        if para_lines and current is not None:
            text = _join(para_lines)
            if text:
                current.paragraphs.append(Paragraph(text, para_page, para_label))
        para_lines = []

    def start_section(sid: str, title: str):
        nonlocal current
        flush_paragraph()
        current = Section(
            chapter_id=chapter_id or "",
            chapter_title=" ".join(chapter_title_parts).strip(),
            code_range=code_range,
            section_id=sid,
            section_title=title.strip(),
        )
        sections.append(current)

    with pdfplumber.open(str(pdf_path)) as pdf:
        for page_no, page in enumerate(pdf.pages, start=1):
            lines, label = _page_lines(page, page_no)
            texts = [ln.text for ln in lines]

            # Table-of-contents pages: many lines end with a page reference ("... I-26").
            if sum(bool(TOC_ENTRY_RE.search(t)) for t in texts) >= 3:
                flush_paragraph()
                chapter_id, current = None, None
                continue

            # Chapter cover pages repeat the AMA copyright notice: reset and skip.
            if any("MEDICARE NATIONAL CORRECT CODING INITIATIVE POLICY MANUAL" in t for t in texts) and any(
                "CPT® is a registered trademark" in t or "Table of Contents" in t for t in texts
            ):
                flush_paragraph()
                chapter_id, current = None, None
                continue

            last_top = None
            for ln in lines:
                # --- chapter start -------------------------------------------------
                m = CHAPTER_RE.match(ln.text)
                if ln.bold and m and ln.x0 > LEFT_MARGIN + 50:
                    flush_paragraph()
                    chapter_id, chapter_title_parts, code_range = m.group(1), [], None
                    current, expected_letter = None, "A"
                    continue
                if ln.bold and ln.text == "Introduction" and chapter_id is None:
                    flush_paragraph()
                    chapter_id, chapter_title_parts, code_range = "Intro", ["Introduction"], None
                    start_section("overview", "Introduction")
                    continue
                if ln.bold and ln.text.upper() == "LIST OF ACRONYMS":
                    flush_paragraph()
                    chapter_id, chapter_title_parts, code_range = "Acronyms", ["List of Acronyms"], None
                    start_section("acronyms", "List of Acronyms")
                    continue
                if chapter_id is None:
                    continue  # still on a cover or table-of-contents page

                # --- chapter title lines (bold, centred, before section A) ---------
                if ln.bold and current is None and not SECTION_RE.match(ln.text):
                    if CODE_RANGE_RE.search(ln.text):
                        code_range = ln.text
                    else:
                        chapter_title_parts.append(ln.text)
                    continue

                # --- section headings -----------------------------------------------
                if ln.bold and abs(ln.x0 - LEFT_MARGIN) < 4:
                    m = SECTION_RE.match(ln.text)
                    if m and m.group(1) == expected_letter:
                        start_section(m.group(1), m.group(2))
                        expected_letter = chr(ord(expected_letter) + 1)
                        last_top = ln.top
                        continue
                    if chapter_id == "Intro":  # unlettered headings in the Introduction
                        slug = re.sub(r"[^a-z0-9]+", "-", ln.text.lower()).strip("-")
                        start_section(slug, ln.text)
                        last_top = ln.top
                        continue

                if current is None:
                    continue

                # --- body text: group lines into paragraphs --------------------------
                gap = None if last_top is None else ln.top - last_top
                if gap is not None and 0 < gap < pitch * 1.2:
                    pitch = 0.9 * pitch + 0.1 * gap
                if gap is None:
                    # First line of a page: continue the previous paragraph unless it
                    # clearly ended (sentence end) and this line starts a new sentence.
                    prev = para_lines[-1] if para_lines else ""
                    new_para = not para_lines or (prev.endswith((".", ":", ";")) and ln.text[:1].isupper())
                else:
                    new_para = not para_lines or gap > pitch * PARAGRAPH_GAP
                new_para = new_para or bool(LIST_MARKER_RE.match(ln.text))
                if chapter_id == "Acronyms":
                    new_para = True  # one acronym per line
                if new_para:
                    flush_paragraph()
                    para_page, para_label = page_no, label
                para_lines.append(ln.text)
                last_top = ln.top
            # A paragraph may continue on the next page; it keeps its starting page.

        flush_paragraph()

    return [s for s in sections if s.paragraphs]
