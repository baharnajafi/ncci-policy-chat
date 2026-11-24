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

# 3b. Optional: the CMS edit tables (PTP code pairs, MUE values) for exact code questions.
#     Download from cms.gov (AMA CPT license click-through; internal use only, never commit them):
#       Practitioner PTP Edits, files f1-f4:  https://www.cms.gov/medicare/coding-billing/national-correct-coding-initiative-ncci-edits/medicare-ncci-procedure-procedure-ptp-edits
#       Practitioner Services MUE Table:      https://www.cms.gov/medicare/coding-billing/national-correct-coding-initiative-ncci-edits/medicare-ncci-medically-unlikely-edits
#     Save the zips in data/edits/ (names must contain "ptp" or "mue"), then (a few seconds, 2.6M rows):
PYTHONPATH=src python -m ncci_rag load-edits

# 4. Ask
PYTHONPATH=src streamlit run app/streamlit_app.py                    # web UI
PYTHONPATH=src python -m ncci_rag ask --debug "What is an MUE?"     # CLI, with retrieval scores
```

If the CMS link has moved, download the PDF from the [CMS NCCI Medicare page](https://www.cms.gov/medicare/coding-billing/national-correct-coding-initiative-ncci-edits/medicare-ncci-policy-manual) and save it under `data/`.

To run without the reranker (no PyTorch download), set `NCCI_RERANKER=none`. To use Azure OpenAI, set `AZURE_OPENAI_ENDPOINT` and `AZURE_OPENAI_API_KEY`; the model settings then name your deployments.

**Tests** run offline, with no key, network, or model download: `pip install -e ".[dev]" && pytest -q` (46 tests, about 10 seconds; 97% line coverage with the PDF present, 86% without). Lint: `ruff check src app eval tests`. CI (`.github/workflows/ci.yml`) runs both on every push, on Python 3.10 and 3.12.

| Test file | What it pins down |
|---|---|
| `test_codes.py`, `test_chunking.py`, `test_models.py` | code/range/modifier extraction, chapter routing, section-aware chunks, citation text |
| `test_store.py` | FTS5 keyword search, vector and chapter filters, code index with ranges, atomic build |
| `test_retrieval.py` | `HybridRetriever.retrieve`: RRF and weights, code routing, reranker order and gate, graph facts passing the gate, the linked section kept in top-k |
| `test_claim_check.py` | invented source IDs, quotes not in the cited source, codes not anchored in the quoted paragraph (the 64450 case) |
| `test_edits.py` | PTP/MUE loader on synthetic CMS-format files, active vs deleted edits by date, facts labelled F |
| `test_pipeline.py` | end to end with a fake chat client: off-topic questions never call the LLM; invented claims are removed; facts reach the prompt; wrong or missing index fails loudly |
| `test_embedder_and_cli.py` | embedding cache across restarts and models, retry on 429/5xx but not 4xx, OpenAI/Azure switch, CLI |
| `test_parser.py` | the parser on the real PDF (skipped if absent), and that each PTP rationale links to the right manual section |

The fakes live in `tests/conftest.py`. The embedder hashes words into a vector, the reranker scores word overlap (0-1), and the chat client returns structured JSON built by each test. They are small, but they behave like the real models in the ways the code depends on.

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

### 5. Grounded generation with a claim check (`generation/answer.py`)
The model sees the top 6 passages labelled `[S1]…[S6]`. It must return strict JSON (OpenAI structured outputs): `answerable`, an optional `not_covered` note, and a list of sentences. Each sentence carries **verbatim quotes** from the passages, the source IDs, and then the sentence itself (quotes come first in the schema, so the sentence is written from the evidence). The code then checks every sentence before showing it:
- **Source check:** source IDs that were not provided are dropped; a sentence with no valid source is removed.
- **Quote check:** each quote must appear (after whitespace and punctuation normalisation) in a passage the sentence cites.
- **Code anchoring:** every CPT/HCPCS code the sentence names must appear, literally or inside a stated range, in its quotes or in the source paragraph each quote comes from.
- If no sentence survives, the answer becomes "not in the manual". Removed sentences are kept on the answer and shown in the UI's debug view.
- Citations are built **from the stored metadata** (chapter, section, page labels), never from text the model wrote.

Why code anchoring: during development, "What is the MUE value for CPT 64450?" produced *"The MUE value for CPT 64450 is one"*, citing the right chunk. But the source sentence, *"The MUEs for these codes are one"*, is about trichiasis codes 67820-67835 in the previous list item. The citation was valid and the claim was wrong. A chunk-level citation check cannot catch this; a paragraph-scoped code check does.

So "not in the manual" has two independent layers: the deterministic gate before the LLM, and the model's own `answerable: false` after reading the passages. The claim check is a third layer for answers that pass both.

### 6. Edit tables as a small knowledge graph (`edits/`)
The manual says *why* codes are bundled. The quarterly CMS edit files say *which* pairs are edited and *how many* units are allowed. Questions like "can I bill 29880 and 29881 together?" or "what is the MUE for 64450?" need both. `load-edits` loads the practitioner PTP file (2.6M rows, 1.7M active) and the MUE table (15K codes) into `data/edits.sqlite`, and `edits/graph.py` reads them as a property graph:

```
(Code)-[:PTP_EDIT {effective, deletion, modifier_indicator}]->(Code)
(PTP_EDIT)-[:BECAUSE]->(Rationale)-[:EXPLAINED_IN]->(Manual section)     e.g. "Mutually exclusive procedures" -> I.P
(PTP_EDIT.modifier_indicator)-[:EXPLAINED_IN]->(I.E Modifiers and Modifier Indicators)
(Code)-[:HAS_MUE {value, adjudication, rationale}]-[:EXPLAINED_IN]->(I.V MUEs)
(Code)-[:IN_RANGE]->(Chapter),  (Section)-[:MENTIONS]->(Code)              already in the manual index
```

When a question names codes, the retriever looks them up (a pair → its edit, or "no edit in either order"; one code + "bundled" → its one-hop edit summary; "MUE / units" → the MUE row). Each row becomes a **fact**: a short passage labelled `[F1]` that the model sees next to the manual passages `[S1]…`. The fact's linked sections become a fifth ranked list, and at least one of their chunks stays in the final passages, so the answer can cite the table row (what) **and** the manual (why). Facts pass through the same claim check as manual passages. Deleted edits are kept and checked against the date of service (default: the file's effective date).

Example: *"What is the MUE value for CPT 64450?"* Before the graph, the model answered "one", borrowing a value stated for other codes. Now: *"The MUE value for CPT code 64450 is 10 units of service. [1] … only one unit of service of CPT code 64450 may be reported per patient encounter … [2]"*, citing `[1] Medicare NCCI MUE table (practitioner services, effective 2026-10-01), MUE 64450` and `[2] Chapter VIII, Section H, p. VIII-18`.

Why SQLite tables and not a graph database: every traversal here is one or two hops on an exact key, which an indexed query answers in under a millisecond. See `docs/DESIGN.md` for when Neo4j would pay off, and why GraphRAG-style community summaries do not fit this corpus.

### Storage
Everything is one SQLite file: chunk metadata, an FTS5 table, vectors stored as float32 BLOBs, and the code tables. At 649 vectors, exact numpy search is about 1 ms and has no recall loss, so an ANN index (HNSW) would add complexity for no gain. `docs/DESIGN.md` covers what changes at scale.

---

## Evaluation

`eval/questions.jsonl` holds three kinds of questions:
- **20 positives**, each labelled with the section(s) that answer it.
- **4 negatives** that are clearly out of scope (Part B premium, a portal password, the Part D formulary, MRI prices). They calibrate the gate.
- **6 fact questions** that need the edit tables: an MUE value, a PTP pair with an edit, a pair with no edit, a deleted edit, a code's edit summary. Each names the fact that must be looked up, and regexes the answer must and must not match.
- **4 hard negatives** that look like coding questions but that neither source answers: a fee schedule amount, an OPPS rate, ICD-10 codes, Medicaid policy. Retrieval finds related policy for these, so the gate lets most of them through. Each has `expect_abstain` or `must_not_match` regexes for the value that would be invented.

The eval reports:
- **hit@1 / hit@3 / hit@6 and MRR** for the final ranking.
- **The rank each retriever alone** gave the first relevant chunk, which shows what BM25, dense, and the code index each contribute.
- **Gate calibration:** a threshold sweep over positives and negatives, with hard negatives reported separately (no retrieval threshold can separate them).
- With `--answers`: whether each positive cites an expected section, whether each hard negative stayed clean, and every sentence the claim check removed, with the reason.

Current results (`eval/RESULTS.md` is a copy of the generated report): hit@1 19/20, MRR 0.96; positives citing an expected section 20/20; fact questions correct 6/6 (all cite the table row); hard negatives clean 3/4. The one failure (Medicaid DME) is a distortion with no code in it, which a lexical check cannot see. See `docs/DESIGN.md`. Two bugs the eval found while building this: the 64450 misattribution (claim check), and a code regex that missed vaccine-administration and MAAA codes such as `0001A` and `0002M`.

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
  edits/loader.py        CMS PTP/MUE zip files -> data/edits.sqlite
  edits/graph.py         edit tables as a property graph; facts + links to manual sections
  generation/answer.py   structured-output prompt and citation validation
  pipeline.py            build_index() and QAPipeline.ask()
  __main__.py            CLI: ingest | ask | chat
app/streamlit_app.py     chat UI: citations expand to the exact passage; debug view
eval/                    labelled questions, eval script
tests/                   offline tests, one file per module; fakes in conftest.py
.github/workflows/ci.yml lint + tests + coverage on every push
docs/DESIGN.md           decisions, trade-offs, what I'd build next
```

## Scope and limits
- **Single-turn questions.** Each question is answered on its own. Follow-ups that depend on the previous answer ("what about for 59?") need query rewriting with chat history. This is the first item in `docs/DESIGN.md`.
- **Practitioner edits only.** The hospital outpatient (OPPS) PTP file, the DME MUE table, and add-on code edits are not loaded yet; the loader handles them the same way. Without `data/edits.sqlite`, the app answers from the manual alone.
- **Date of service.** Edit lookups use the file's effective date; the question's own date is not parsed yet.
- This is a reference tool, not billing advice for a specific claim.
