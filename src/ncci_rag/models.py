"""Core data types shared across ingestion, retrieval, and generation."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Paragraph:
    """A paragraph of body text with the location it came from."""

    text: str
    page: int  # 1-based PDF page number
    page_label: str  # page number printed in the manual, e.g. "I-15"


@dataclass
class Section:
    """A lettered section of a chapter (e.g. Chapter I, Section E), or an unlettered
    section such as the Introduction's "Purpose"."""

    chapter_id: str  # "Intro", "I", "II", ..., "XIII", "Acronyms"
    chapter_title: str  # "General Correct Coding Policies"
    code_range: str | None  # "CPT Codes 20000 - 29999", if the chapter states one
    section_id: str  # "E", or a slug for unlettered sections
    section_title: str  # "Modifiers and Modifier Indicators"
    paragraphs: list[Paragraph] = field(default_factory=list)


@dataclass
class Chunk:
    """The unit that is indexed, retrieved, and cited."""

    chunk_id: str  # stable: "<chapter>.<section>.<n>", e.g. "I.E.03"
    chapter_id: str
    chapter_title: str
    code_range: str | None
    section_id: str
    section_title: str
    page_start: int
    page_end: int
    label_start: str
    label_end: str
    text: str  # the passage itself, shown to the user and to the model
    codes: list[str] = field(default_factory=list)  # CPT/HCPCS codes mentioned
    modifiers: list[str] = field(default_factory=list)  # modifiers mentioned

    @property
    def heading(self) -> str:
        """Human-readable location, used in citations."""
        chapter = "Introduction" if self.chapter_id == "Intro" else f"Chapter {self.chapter_id}"
        if self.chapter_id == "Acronyms":
            chapter = "List of Acronyms"
        sect = (
            f"Section {self.section_id}. {self.section_title}"
            if len(self.section_id) == 1
            else self.section_title
        )
        return f"{chapter} ({self.chapter_title}) – {sect}"

    @property
    def pages(self) -> str:
        if self.label_start == self.label_end:
            return f"p. {self.label_start} (PDF p. {self.page_start})"
        return f"pp. {self.label_start}–{self.label_end} (PDF pp. {self.page_start}–{self.page_end})"

    @property
    def context_header(self) -> str:
        """Prepended to the text before embedding and keyword indexing, so a chunk is
        retrievable by the chapter and section it belongs to, not only by its own words."""
        rng = f" [{self.code_range}]" if self.code_range else ""
        return f"{self.heading}{rng}"


@dataclass
class ScoredChunk:
    chunk: Chunk
    score: float  # meaning depends on stage: RRF score, or reranker relevance (0-1)
    ranks: dict[str, int] = field(default_factory=dict)  # rank in each retriever, for debugging


@dataclass
class Citation:
    source_id: str  # "S1", as shown to the model
    chunk: Chunk


@dataclass
class AnswerSentence:
    text: str
    source_ids: list[str]


@dataclass
class Answer:
    question: str
    answerable: bool
    sentences: list[AnswerSentence]
    citations: list[Citation]  # only sources actually cited, in order of first use
    retrieved: list[ScoredChunk]  # everything the model saw, for transparency
    reason: str = ""  # why there is no answer, when answerable is False

    @property
    def text(self) -> str:
        if not self.answerable:
            return self.reason or "The manual does not appear to answer this question."
        order = {c.source_id: i + 1 for i, c in enumerate(self.citations)}
        parts = []
        for s in self.sentences:
            marks = "".join(f"[{order[sid]}]" for sid in s.source_ids if sid in order)
            parts.append(f"{s.text} {marks}".strip())
        return " ".join(parts)
