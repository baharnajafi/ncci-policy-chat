# Deploying the app with a public link

The app runs on **Streamlit Community Cloud** (free; deploys from a public GitHub repo
and gives an `https://<name>.streamlit.app` link). **Hugging Face Spaces** is the
fallback if the container runs out of memory (see the end of this page).

Nothing secret or licensed is in the repository. The hosted app starts from the code alone:

| What | Where it comes from on the hosted app |
|---|---|
| OpenAI key, password, settings | the platform's secret store (`st.secrets`), copied into env vars at startup (`ncci_rag/bootstrap.py`) |
| The manual PDF | downloaded from cms.gov on first start (public document) |
| The index (`data/index.sqlite`) | built on first start: parse + embed, about 30 seconds and a few cents |
| CMS PTP/MUE edit tables | **not deployed.** Their AMA CPT license allows internal use only, so the public app answers from the manual alone. The sidebar says "Edit tables loaded: no". |

## Steps (Streamlit Community Cloud)

1. Push the repository to a **public** GitHub repo. Check first that `git status` shows no
   `.env`, `.streamlit/secrets.toml`, `data/*.pdf`, `data/*.sqlite`, or `data/edits/` (all
   are in `.gitignore`).
2. On https://share.streamlit.io, sign in with GitHub and choose **Create app → Deploy a
   public app from GitHub**:
   - Repository: your repo; Branch: `main`
   - Main file path: `app/streamlit_app.py`
   - App URL: pick a name, e.g. `ncci-policy-chat`
   - Advanced settings → Python version: 3.12
3. In **Advanced settings → Secrets**, paste (see `.streamlit/secrets.toml.example`):

   ```toml
   OPENAI_API_KEY = "sk-..."
   APP_PASSWORD = "choose-a-password"     # share it with the reviewers
   NCCI_MAX_QUESTIONS = "25"               # per browser session
   NCCI_RERANKER = "cross-encoder/ms-marco-MiniLM-L-6-v2"
   NCCI_MIN_RELEVANCE = "0.30"
   ```

4. Deploy. The first start installs dependencies (a few minutes, CPU-only PyTorch), then the
   first visitor after the password sees "First start: downloading the manual and building
   the index", which takes about a minute. Later visits are immediate, until the platform
   recycles the container; then the index is rebuilt once more.
5. Put the link and the password in the README or in the email to reviewers.

To test the hosted setup locally, create `.streamlit/secrets.toml` from the example, and
start from a copy without `data/index.sqlite`: `streamlit run app/streamlit_app.py`.

## Why these settings

**Password and question limit.** A public link spends the OpenAI key. The password is a
shared secret checked in constant time (`hmac.compare_digest`); the limit caps cost per
browser session. Neither is real authentication. For more than a demo, put the app
behind SSO (e.g. Azure App Service with Entra ID) and rate-limit per user.

**A smaller reranker on the hosted app.** Community Cloud containers have limited memory.
Measured on this machine, same 30 candidates:

| Reranker | Peak memory (incl. PyTorch) | Load + score 30 pairs | Eval: hit@1 / hit@3 / MRR | Gate margin (lowest positive vs highest negative) |
|---|---|---|---|---|
| `BAAI/bge-reranker-base` (local default) | ~1150 MB | 2.5 s | 19/20 · 19/20 · 0.96 | 0.78 vs 0.05 |
| `cross-encoder/ms-marco-MiniLM-L-6-v2` (hosted) | ~650 MB | 1.3 s | 19/20 · 20/20 · 0.97 | 0.96 vs 0.004 |

On this eval set the small model is as good or better, and the same gate threshold (0.30)
separates in-scope from out-of-scope questions with a wider margin. It is English-only
and trained on web search queries (MS MARCO), so I would re-run `eval/run_eval.py` before
using it on other documents. The local default stays `bge-reranker-base` so the recorded
results in `eval/RESULTS.md` stay comparable.

**CPU-only PyTorch.** `requirements.txt` adds the PyTorch CPU wheel index. Without it, pip on
Linux installs the CUDA build (several GB), which a CPU container cannot use.

## Things the local tests and a simulated cloud start caught

Before writing this page, the app was started the way the platform starts it: a clean copy
of the repo, a fresh environment from `requirements.txt`, secrets only in
`.streamlit/secrets.toml`, no `.env`, PDF, or index. That run (and the first CI run) found four problems, now fixed
and covered by tests:

1. **Second question failed** with "SQLite objects created in a thread can only be used in
   that same thread". Streamlit caches the pipeline once but runs every rerun (and every
   visitor) on its own thread. All SQLite access now goes through one locked connection
   (`index/db.py`); `tests/test_threads.py` reproduces the failure without the fix.
2. **Settings from secrets were ignored** for numeric values (`NCCI_TOP_K`,
   `NCCI_MIN_RELEVANCE`, ...), because they were read when `config.py` was imported, before
   the secrets were applied. They are now read when `Settings()` is created
   (`tests/test_config.py`).
3. **Two threads loading a cold index at once** (found by the first CI run, on Python 3.12):
   lazy loading published an empty dict before filling it, so another thread could look up
   a chunk too early. Chunks and vectors are now built locally and published in one
   assignment under a lock; `test_cold_store_loaded_by_many_threads_at_once` fails on the old
   code every time.
4. **A question sent while another was running lost its answer** (Streamlit stops the
   running script when new input arrives). The chat now marks such a question as
   interrupted instead of leaving it without a reply.

## Fallback: Hugging Face Spaces

If the Community Cloud container runs out of memory, create a Space with the **Docker**
SDK (free CPU tier, 16 GB RAM), add the same values as Space **secrets**, and use a
Dockerfile that runs `pip install -r requirements.txt` and
`streamlit run app/streamlit_app.py --server.port 7860 --server.address 0.0.0.0`. The
app code needs no change: `bootstrap.py` reads the secrets from the environment either way.
