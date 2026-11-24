# Design notes

Decisions, the alternatives I considered, and what I would build next. The goal was a small system where retrieval quality and grounding can be **measured**, rather than a large system that is hard to evaluate.

## 1. Decisions and trade-offs

| Decision | Chosen | Alternatives | Why |
|---|---|---|---|
| PDF parsing | `pdfplumber` with layout signals (bold, x-position, footer zone, line gaps) | `pypdf` text, generic "unstructured" loaders, fixed-size splitting | The manual's structure (chapter → lettered section → paragraph, plus printed page labels) is what citations need. `pypdf` split words ("R\nevision"). Generic loaders lose the section hierarchy. |
| Chunk unit | Section-aware, ~250 words (max 400), never crosses a section | Fixed 512 tokens with overlap; one chunk per section | One chunk maps to exactly one citable section. Some sections are many pages long, so one chunk per section is too coarse for ranking and wastes context. With section boundaries there is no need for overlap. |
| Contextual header | Chapter + section title + code range prepended before embedding and FTS | Embed raw text only | Many paragraphs never repeat their topic ("the procedure is not separately reportable"). The header makes them findable by chapter and section. |
| Lexical retrieval | SQLite FTS5 BM25, porter stemming, header weighted 0.5 / body 1.0 | Elasticsearch/OpenSearch | Same algorithm, no server. Coding vocabulary (MUE, PTP, XS, "add-on") needs exact matching that dense retrieval often misses. |
| Dense retrieval | `text-embedding-3-large` (3072-d), exact cosine in numpy | HNSW / FAISS / a vector DB | At ~650 vectors, exact search takes about a millisecond and has perfect recall. An ANN index only pays off around 10⁵ vectors or more. |
| Code retrieval | Regex code index: exact codes, **ranges**, modifiers; chapter routing by code range | Rely on BM25 for codes | The manual mostly states ranges ("CPT codes 64400-64530"), and BM25 cannot match 64450 to that. Routing sends 27447 to Chapter IV's general rules. |
| Fusion | RRF, k = 60; chapter-routed list at weight 0.5 | Weighted score blending | The scores are on incompatible scales. RRF needs no normalization and copes when a retriever returns nothing. |
| Reranking | Cross-encoder `bge-reranker-base` over the top 30 | LLM-as-reranker; none | It improves the order, and it provides an absolute relevance score for the gate. An LLM reranker costs more and is slower for this. |
| Abstention | (a) deterministic gate on the top reranker score before the LLM; (b) `answerable=false` from the model | Prompt-only "say I don't know" | Prompt-only abstention is unreliable when the context is plausible but irrelevant. The gate is cheap and calibrated on labelled negatives. It also never sends irrelevant text to the model. |
| Citations | Per-sentence source IDs in strict JSON; validated in code; rendered from stored metadata | Ask the model to write citations in prose | The model cannot invent a page number, because it never writes one. Unsupported sentences are removed rather than shown. |
| Claim check | Per-sentence verbatim quotes; quote must be in the cited passage; every named code must be in the quote's source paragraph (or a range there) | Trust chunk-level citations; LLM-as-judge on every sentence | A valid chunk citation does not mean a valid claim (the 64450 / trichiasis case in the README). The lexical checks are deterministic, free, and testable offline. Paragraph scope matches how the manual writes rules (one per paragraph or list item). An entailment judge is the next layer, for claims with no code in them. |
| Storage | One SQLite file, built atomically (`.building` → rename); meta records the PDF hash and embed model | Postgres + pgvector | No infrastructure for a reviewer to run. The meta check refuses to query an index built with a different embedding model. |
| Provider | OpenAI, or Azure OpenAI through one env switch | — | Swapping to Azure is a configuration change, not a code change. |
| UI | Streamlit, minimal | React | The exercise is about retrieval and grounding. The UI only needs to show answers, expandable citations, and a debug view. |

## 2. How quality is measured
`eval/run_eval.py` scores the final ranking (hit@k, MRR). It also records **each retriever's own rank** for the first relevant chunk, so you can see which component found it. It sweeps the gate threshold over positive and negative questions, so the threshold comes from data rather than a guess. With `--answers`, it also checks that generated answers cite a section labelled as correct.

Every tunable (models, candidate counts, k, threshold) is an environment variable, and the report prints the settings it ran with. A change is then a one-line experiment with a comparable report.

**Known limit of the eval:** 31 questions, written and labelled by one person. It catches regressions and makes the gate calibration concrete, but it is not a statistically strong benchmark. The next step is 100+ questions, drafted from section headings by an LLM and **reviewed by a coding expert**, with more hard negatives that sound in-domain. The first 7 are already in the set (MUE values, PTP pairs, fee schedule and OPPS rates, ICD-10, Medicaid).

**What the claim check cannot see.** It is lexical. It catches invented quotes and codes borrowed from another rule, but not a distortion with no code in it. The remaining hard-negative failure is an example: the manual says reconsideration requests should name the program (Medicare or Medicaid) and the edit type (for example DME), and the model turned that into a statement about Medicaid DME edits. It also over-rejects a little: a long list of codes the model only partly quoted, or a quote it stitched from two sentences. The trade-off is deliberate, because a coder is better served by a shorter answer than by a confident wrong one.

## 3. What I would build next

**0. Entailment check per sentence.** Add an NLI model or a small LLM judge that scores each (quote, sentence) pair, run only on sentences that pass the lexical checks. Gate it with the hard-negative set, and report removed sentences as today.

**1. Conversational follow-ups.** Rewrite the question using the chat history before retrieval ("what about with modifier 25?" → a standalone question). The history is used only for retrieval; the answer is still grounded only in retrieved passages.

**2. Join the NCCI edit tables (a knowledge graph).** The manual is the *why*; the quarterly PTP and MUE files are the *what*. A small graph makes questions like "can 64450 and 64447 be billed together, and why?" answerable exactly:

```
(Code)-[:IN_RANGE]->(CodeRange)-[:GOVERNED_BY]->(Chapter)-[:HAS_SECTION]->(Section)
(Code)-[:PTP_EDIT {modifier_indicator, effective, deleted}]->(Code)
(Code)-[:HAS_MUE {units, adjudication_indicator}]->(MUE)
(Section)-[:MENTIONS]->(Code | Modifier)
(Modifier)-[:BYPASSES]->(PTP_EDIT where indicator = 1)
```

A typed lookup ("is there a PTP edit for A + B? what is the indicator?") answers the fact. Retrieval over the manual explains the policy. The answer cites both. The current code index and chapter routing are the first layer of this graph (codes, ranges, and mentions), stored as tables.

**3. Production path.**
- **Index:** at a scale of many manuals or versions, use a managed hybrid index (Azure AI Search or OpenSearch with BM25, HNSW, and a semantic reranker) or Postgres with pgvector and full-text search. Keep the same retriever interface.
- **Versioning:** CMS publishes yearly manuals and quarterly edit files. Add effective dates and version IDs to chunk metadata, filter by the date of service, and cite the version.
- **Evaluation in CI:** run the eval on every change to the parser, chunking, or prompt, and block merges that regress hit@k or let a negative through.
- **Monitoring:** log question, retrieved IDs, scores, gate decision, and cited IDs. Track the abstention rate and get user feedback per citation.
- **Security:** keep keys in a secret store, add authentication on the UI, and redact PHI if users paste claim details.
- **Latency/cost:** the embedding cache already avoids re-embedding at ingest. At query time, the cost is one embedding plus one rerank on CPU plus one chat call. Streaming the answer would improve perceived latency.

## 4. Things I deliberately did not do
- **No agent loop.** One retrieval pass plus validation answers these questions. An agent (plan → search → reflect) adds latency and failure modes without measured benefit here. It becomes worthwhile once there are several tools, such as the edit-table lookup above.
- **No LangChain or LlamaIndex.** The pipeline is about 1,200 lines and every step is visible and testable. A framework would hide the parts the exercise is meant to evaluate.
- **No fine-tuning.** Retrieval quality is measured first. The reranker and the eval set are the right levers at this size.
