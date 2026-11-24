# NCCI Policy Manual Chat

Ask questions about the **CMS 2026 Medicare NCCI Policy Manual** and get answers that come only from the manual. Every sentence in an answer cites the chapter, section, and page it came from. When the manual does not cover a question, the app says so instead of guessing.

Each answer is followed by its sources, in this format (taken from the real index):

```
Sources:
  [1] Chapter I (General Correct Coding Policies) – Section E. Modifiers and Modifier Indicators, p. I-14 (PDF p. 30)
  [2] Chapter IV (Surgery: Musculoskeletal System) – Section E. Arthroscopy, pp. IV-5–IV-6 (PDF pp. 87–88)
```

In the UI, each citation expands to show the exact passage.

---

## Quick start

Requires Python 3.10+ and an OpenAI API key.

```bash
git clone https://github.com/<you>/ncci-policy-chat && cd ncci-policy-chat
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 1. The manual (287 pages). Not committed to the repo.
curl -L -o data/2026_ncci_medicare_policy_manual_all-chapters.pdf \
  https://www.cms.gov/files/document/2026-ncci-medicare-policy-manual-all-chapters.pdf

# 2. Your key, in a local .env file (git-ignored)
cp .env.example .env        # then edit OPENAI_API_KEY

# 3. Build the index: parse -> chunk -> embed (a minute or two; about 650 chunks, a few cents of embeddings)
PYTHONPATH=src python -m ncci_rag ingest

# 4. Ask
PYTHONPATH=src streamlit run app/streamlit_app.py                    # web UI
PYTHONPATH=src python -m ncci_rag ask --debug "What is an MUE?"     # CLI, with retrieval scores
```

If the CMS link has moved, download the PDF from the [CMS NCCI Medicare page](https://www.cms.gov/medicare/coding-billing/national-correct-coding-initiative-ncci-edits/medicare-ncci-policy-manual) and save it under `data/`.

To run without the reranker (no PyTorch download), set `NCCI_RERANKER=none`. To use Azure OpenAI, set `AZURE_OPENAI_ENDPOINT` and `AZURE_OPENAI_API_KEY`; the model settings then name your deployments.

**Tests** run offline, with no key: `pytest -q`

**Evaluation:** `PYTHONPATH=src python eval/run_eval.py` (add `--answers` to grade generated answers too). It writes `eval/report.md`.

---

## How it works

```
                 INGEST (once)                                         QUERY (per question)

 PDF ──► layout-aware parser ──► sections ──► chunker ──► chunks     question
         (bold headings, page                 (~250 words,             │
          labels, TOC/cover skip)             never crosses           ├─► BM25 (SQLite FTS5) ─────┐
                                              a section)              ├─► dense (cosine) ─────────┤
                                                 │                    ├─► code/modifier index ────┼─► RRF ─► cross-encoder ─► relevance ──► LLM, JSON ──► validate
                                                 ▼                    └─► routed chapter (codes) ─┘  fuse    rerank top 30    gate        per-sentence  citation IDs
                          SQLite: chunks · FTS5 · vectors · code_mentions · code_ranges                                         │           source IDs
                                                                                                                  below threshold ▼
                                                                                                             "not in the manual" (no LLM call)
```

### 1. Parsing that keeps the manual's structure (`ingest/pdf_parser.py`)
The manual has a regular layout: bold, left-aligned lettered headings ("E. Modifiers and Modifier Indicators"), a printed page label in the footer ("I-16"), and a table of contents and cover page in every chapter. The parser reads these layout signals with `pdfplumber` and produces **145 sections** in 15 parts: the Introduction, Chapters I–XIII, and the acronym list. Each paragraph keeps its PDF page and printed page label, so a citation can say "p. I-14 (PDF p. 30)". It skips TOC and cover pages, because they would otherwise match almost every query.

### 2. Section-aware chunking (`ingest/chunker.py`)
Chunks are about 250 words (400 at most) and never cross a section boundary, so every chunk has one correct citation. Breaks prefer list items, then sentence ends. Each chunk is embedded and keyword-indexed with a **context header**: "Chapter IV (Surgery: Musculoskeletal System) – Section E. Arthroscopy [CPT Codes 20000 - 29999]". A paragraph that only says "the diagnostic arthroscopy is not separately reportable" can then still be found by chapter and topic. The result is 649 chunks, with a median of 159 words.

### 3. Three retrievers, fused by rank (`retrieval/hybrid.py`)
| Retriever | Good at | Example |
|---|---|---|
| **BM25** (SQLite FTS5, porter stemming) | exact vocabulary | "MUE", "XS", "add-on code" |
| **Dense** (`text-embedding-3-large`, exact cosine) | paraphrase | "bill two procedures on the same day" ≈ "reported together" |
| **Code / modifier index** | identifiers and **ranges** | "64450" matches a chunk that says "CPT codes 64400-64530" |

When a question names a code, the code is also **routed to its chapter** by the chapter's code range (27447 → Chapter IV, 20000–29999). A fourth, half-weight list searches within that chapter, because the chapter's general rules apply even where the code itself is never named.

The lists are fused with **Reciprocal Rank Fusion** (k = 60). The retrievers' scores are on different scales (BM25, cosine, match counts), and RRF uses only their ranks.

### 4. Rerank, then a relevance gate
The top 30 fused candidates are rescored by a cross-encoder (`BAAI/bge-reranker-base`), which reads the question and the passage together. This gives the final order, and it also gives a score that is *comparable across questions*. RRF scores cannot serve this purpose: they only say how a passage ranked, not whether it is relevant. If the best reranker score is below `NCCI_MIN_RELEVANCE`, the app answers "not in the manual" **without calling the LLM**. The threshold is calibrated by `eval/run_eval.py`; see below.

### 5. Grounded generation with validated citations (`generation/answer.py`)
The model sees the top 6 passages labelled `[S1]…[S6]`. It must return strict JSON (OpenAI structured outputs): `answerable`, plus a list of `{sentence, source_ids}`. The code then validates the response:
- Source IDs that were not provided are dropped. A sentence left with no valid source is removed.
- If no sentence survives, the answer becomes "not in the manual".
- Citations are built **from the stored metadata** (chapter, section, page labels), never from text the model wrote.

So "not in the manual" has two independent layers: the deterministic gate before the LLM, and the model's own `answerable: false` after reading the passages.

### Storage
Everything is one SQLite file: chunk metadata, an FTS5 table, vectors stored as float32 BLOBs, and the code tables. At 649 vectors, exact numpy search is about 1 ms and has no recall loss, so an ANN index (HNSW) would add complexity for no gain. `docs/DESIGN.md` covers what changes at scale.

---

## Evaluation

`eval/questions.jsonl` holds 20 policy questions, each labelled with the section(s) that answer it, and 4 out-of-scope questions (Part B premium, a portal password, the Part D formulary, MRI prices). The eval reports:

- **hit@1 / hit@3 / hit@6 and MRR** for the final ranking.
- **The rank each retriever alone** gave the first relevant chunk, which shows what BM25, dense, and the code index each contribute.
- **Gate calibration:** the top relevance score for every question, and a threshold sweep. The chosen threshold should pass every in-scope question and block every out-of-scope one.

Results for the committed configuration are in [`eval/RESULTS.md`](eval/RESULTS.md), which is a copy of the generated report.

---

## Repository layout

```
src/ncci_rag/
  models.py              Paragraph, Section, Chunk, Answer, Citation (typed, no logic)
  config.py              all tunables from env (.env), so experiments need no code changes
  llm_client.py          OpenAI or Azure OpenAI client
  ingest/pdf_parser.py   layout-aware PDF -> sections with page labels
  ingest/chunker.py      section-aware chunks with code/modifier extraction
  ingest/codes.py        CPT/HCPCS/Cat III codes, ranges, modifiers, chapter routing
  index/embedder.py      batched embeddings with retry and an on-disk cache
  index/store.py         SQLite: FTS5, vectors, code index; atomic build
  retrieval/hybrid.py    BM25 + dense + codes -> RRF -> rerank -> gate
  retrieval/rerank.py    cross-encoder reranker
  generation/answer.py   structured-output prompt and citation validation
  pipeline.py            build_index() and QAPipeline.ask()
  __main__.py            CLI: ingest | ask | chat
app/streamlit_app.py     chat UI: citations expand to the exact passage; debug view
eval/                    labelled questions, eval script
tests/                   offline unit tests (fake embedder, no key)
docs/DESIGN.md           decisions, trade-offs, what I'd build next
```

## Scope and limits
- **Single-turn questions.** Each question is answered on its own. Follow-ups that depend on the previous answer ("what about for 59?") need query rewriting with chat history. This is the first item in `docs/DESIGN.md`.
- **Policy text, not the edit tables.** The manual explains the rules; the actual PTP and MUE edit pairs are separate CMS data files. Joining them is the main next step (see DESIGN.md).
- This is a reference tool, not billing advice for a specific claim.
