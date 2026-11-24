# Run the app on your own computer (step by step)

This guide assumes a Mac. Windows notes are in brackets. It takes about 15 minutes, most of
it waiting for downloads.

## 1. Install the tools (once)

1. **Python 3.10 or newer.**
   - Check: open the Terminal app and run `python3 --version`.
   - If it is missing or older than 3.10, install it from https://www.python.org/downloads/
     (or `brew install python@3.12` if you use Homebrew).
     [Windows: install from python.org and tick "Add python.exe to PATH".]
2. **Git.** Check with `git --version`. On a Mac, if it is missing, the system offers to install
   the Command Line Tools; accept. [Windows: https://git-scm.com/download/win]
3. **Visual Studio Code** (optional, but the easiest way to read and run the code):
   - Download from https://code.visualstudio.com/ and drag it into Applications.
   - Open it, go to the Extensions view (the four-squares icon on the left), and install
     **Python** (by Microsoft). It also installs **Pylance**.
   - Optional: install **Ruff** (by Astral) for lint-on-save.
4. **An OpenAI API key** from https://platform.openai.com/api-keys. Building the index costs
   a few cents; each question costs well under a cent.

## 2. Get the code

```bash
cd ~/Documents
git clone https://github.com/baharnajafi/ncci-policy-chat.git
cd ncci-policy-chat
```

In VS Code: **File → Open Folder…** and choose `ncci-policy-chat`. Open a terminal inside VS
Code with **Terminal → New Terminal**. Every command below runs in that terminal, from the
project folder.

## 3. Create a virtual environment and install the dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate          # [Windows: .venv\Scripts\activate]
pip install --upgrade pip
pip install -r requirements.txt    # a few minutes: includes PyTorch (CPU) and Streamlit
pip install -e ".[dev]"            # pytest and ruff, for running the tests
```

The prompt now starts with `(.venv)`. In VS Code, press **Cmd+Shift+P → "Python: Select
Interpreter"** and pick the one in `.venv`, so the editor uses the same packages.

## 4. Add your API key

```bash
cp .env.example .env
```

Open `.env` in VS Code and set `OPENAI_API_KEY=sk-...` (your key, no quotes). `.env` is in
`.gitignore`, so it is never committed.

## 5. Download the manual and build the index

```bash
curl -L -o data/2026_ncci_medicare_policy_manual_all-chapters.pdf \
  https://www.cms.gov/files/document/2026-ncci-medicare-policy-manual-all-chapters.pdf

PYTHONPATH=src python -m ncci_rag ingest
```

You should see `Parsed 145 sections into 649 chunks`, then `Index written to
data/index.sqlite` (about 30 seconds).
[Windows PowerShell: run `$env:PYTHONPATH="src"` once, then `python -m ncci_rag ingest`.]

If you skip this step, the Streamlit app does it by itself on first start.

## 6. Optional: the CMS edit tables (exact answers for code pairs and MUE values)

1. Open the CMS pages below. Each download asks you to accept the AMA CPT license (internal
   use only; never commit these files).
   - PTP edits: https://www.cms.gov/medicare/coding-billing/national-correct-coding-initiative-ncci-edits/medicare-ncci-procedure-procedure-ptp-edits
     → under **Practitioner PTP Edits**, download all 4 zip files (f1 to f4).
   - MUE table: https://www.cms.gov/medicare/coding-billing/national-correct-coding-initiative-ncci-edits/medicare-ncci-medically-unlikely-edits
     → **Practitioner Services MUE Table (ZIP)**.
2. Move the 5 zip files into `data/edits/` and rename them so the names contain `ptp` or
   `mue` (for example `ptp-f1.zip` … `ptp-f4.zip`, `mue.zip`).
3. Load them (a few seconds):

   ```bash
   PYTHONPATH=src python -m ncci_rag load-edits
   ```

Without this step everything still works; answers then come from the manual alone.

## 7. Start the app and open it in your browser

```bash
PYTHONPATH=src streamlit run app/streamlit_app.py
```

The browser opens http://localhost:8501 by itself (if not, open that address). The first
question takes a few seconds longer while the reranker model downloads (about 1 GB, once).
To stop the app, press **Ctrl+C** in the terminal.

## 8. Test it with questions

Type these into the chat box. In the left sidebar, turn on **Show retrieval details** to see
scores, the per-retriever ranks, and any sentences the claim check removed.

| Question | What you should see |
|---|---|
| When is modifier 59 appropriate? | Several sentences, citing Chapter I, Section E (pp. I-17 and later) |
| What is a Medically Unlikely Edit (MUE)? | A definition citing Chapter I, Section V |
| Can an E&M service be reported on the same day as a minor surgical procedure? | Only with a significant, separately identifiable service and modifier 25 |
| If a diagnostic arthroscopy leads to a surgical arthroscopy, can both be reported? | No, only the surgical one; cites Chapter IV, Section E |
| What is the 2026 Medicare Part B monthly premium? | "I couldn't find this in the manual" (the relevance gate; no LLM call) |
| What is the MUE value for CPT 64450? | With edit tables: **10**, citing the MUE table and Chapter VIII. Without them: one unit per encounter, and a note that the manual does not list the value |
| Can CPT 29880 and 29881 be reported together for the same knee? | With edit tables: an active PTP edit (29880 Column One, modifier indicator 1), citing the edit and Chapter I |

Click a citation to expand it. It shows the exact quote the answer used, then the full
passage, with chapter, section, and page numbers.

## 9. Other ways to run it

```bash
PYTHONPATH=src python -m ncci_rag ask --debug "What is an MUE?"   # one question in the terminal
PYTHONPATH=src python -m ncci_rag chat                             # interactive terminal chat
pytest -q                                                          # 53 offline tests, ~10 seconds
ruff check src app eval tests                                      # lint
PYTHONPATH=src python eval/run_eval.py                             # retrieval eval (writes eval/report.md)
PYTHONPATH=src python eval/run_eval.py --answers                   # also grades generated answers
```

## Troubleshooting

| Message | Fix |
|---|---|
| `OPENAI_API_KEY is not set` | Step 4: check that `.env` exists in the project folder and has the key |
| `No index at data/index.sqlite` | Step 5 (or just start the Streamlit app, which builds it) |
| `ModuleNotFoundError: ncci_rag` | Add `PYTHONPATH=src` before the command, or run `pip install -e .` once |
| `Index was built with ... but NCCI_EMBED_MODEL is ...` | You changed the embedding model; run step 5 again |
| Port 8501 is busy | `streamlit run app/streamlit_app.py --server.port 8502` |
| `command not found: python` | Use `python3`, or activate the virtual environment (step 3) |
