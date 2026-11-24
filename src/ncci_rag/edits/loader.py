"""Load the CMS Medicare NCCI practitioner edit files into SQLite.

Inputs (downloaded by the user from cms.gov, under the AMA CPT license; never
committed, see README):

* PTP edits, 4 zip files: ``ccipra-vXXXrY-f1..f4``, each with a tab-separated TXT
  (Column 1, Column 2, *=in existence prior to 1996, Effective, Deletion ("*" = none),
  Modifier indicator 0/1/9, PTP Edit Rationale). About 2.6M rows, 1.7M still active;
  deleted edits are kept because the edit that applies depends on the date of service.
* MUE table, 1 zip: a CSV (code, MUE value, MUE adjudication indicator, rationale)
  after a few lines of AMA copyright text.

Output: ``data/edits.sqlite`` with tables ``ptp``, ``mue``, and ``meta``.
"""

from __future__ import annotations

import csv
import io
import re
import sqlite3
import zipfile
from pathlib import Path

CODE_RE = re.compile(r"^[0-9A-Z]{5}$")
VERSION_RE = re.compile(r"(v\d{3}r\d)", re.I)
MUE_EFF_RE = re.compile(r"Eff_(\d{2})-(\d{2})-(\d{4})")

SCHEMA = """
CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT);
-- One row per edit (Column One code, Column Two code, effective period).
CREATE TABLE ptp (
    col1 TEXT, col2 TEXT, effective INTEGER, deletion INTEGER,  -- YYYYMMDD; deletion NULL = active
    modifier_indicator INTEGER, rationale TEXT
);
CREATE TABLE mue (code TEXT PRIMARY KEY, value INTEGER, adjudication TEXT, rationale TEXT);
"""


def _ptp_rows(zf: zipfile.ZipFile):
    name = next(n for n in zf.namelist() if n.lower().endswith(".txt"))
    with zf.open(name) as fh:
        for raw in io.TextIOWrapper(fh, encoding="latin-1"):
            cols = raw.rstrip("\r\n").split("\t")
            if len(cols) < 7 or not CODE_RE.match(cols[0]) or not CODE_RE.match(cols[1]):
                continue  # header and copyright lines
            deletion = None if cols[4].strip() in ("", "*") else int(cols[4])
            yield cols[0], cols[1], int(cols[3]), deletion, int(cols[5]), cols[6].strip()


def _mue_rows(zf: zipfile.ZipFile):
    name = next(n for n in zf.namelist() if n.lower().endswith(".csv"))
    with zf.open(name) as fh:
        for row in csv.reader(io.TextIOWrapper(fh, encoding="latin-1")):
            if len(row) >= 4 and CODE_RE.match(row[0].strip()) and row[1].strip().isdigit():
                yield row[0].strip(), int(row[1]), row[2].strip(), row[3].strip()


def load_edits(edits_dir: Path, db_path: Path, log=print) -> Path:
    edits_dir, db_path = Path(edits_dir), Path(db_path)
    ptp_zips = sorted(p for p in edits_dir.glob("*.zip") if "ptp" in p.name.lower())
    mue_zips = sorted(p for p in edits_dir.glob("*.zip") if "mue" in p.name.lower())
    if not ptp_zips and not mue_zips:
        raise FileNotFoundError(f"No PTP or MUE zip files in {edits_dir}. See README for the download links.")

    tmp = db_path.with_suffix(".building")
    tmp.unlink(missing_ok=True)
    conn = sqlite3.connect(tmp)
    conn.executescript(SCHEMA)
    meta: dict[str, str] = {"ptp_setting": "practitioner"}
    with conn:
        for zp in ptp_zips:
            with zipfile.ZipFile(zp) as zf:
                conn.executemany("INSERT INTO ptp VALUES (?,?,?,?,?,?)", _ptp_rows(zf))
                if m := VERSION_RE.search(" ".join(zf.namelist())):
                    meta["ptp_version"] = m.group(1)
            log(f"  loaded {zp.name}")
        for zp in mue_zips:
            with zipfile.ZipFile(zp) as zf:
                conn.executemany("INSERT OR REPLACE INTO mue VALUES (?,?,?,?)", _mue_rows(zf))
                if m := MUE_EFF_RE.search(" ".join(zf.namelist())):
                    meta["mue_effective"] = f"{m.group(3)}{m.group(1)}{m.group(2)}"
            log(f"  loaded {zp.name}")
        # The newest effective date in the PTP file is the version's own effective date
        # (quarterly files carry every edit since 1996).
        if ptp_zips:
            latest = conn.execute("SELECT max(effective) FROM ptp").fetchone()[0]
            meta["ptp_effective"] = str(latest)
        for k, v in meta.items():
            conn.execute("INSERT INTO meta VALUES (?, ?)", (k, v))
    conn.executescript("""
        CREATE INDEX ptp_pair ON ptp(col1, col2);
        CREATE INDEX ptp_col2 ON ptp(col2);
    """)
    n_ptp = conn.execute("SELECT count(*) FROM ptp").fetchone()[0]
    n_mue = conn.execute("SELECT count(*) FROM mue").fetchone()[0]
    conn.close()
    tmp.replace(db_path)
    log(f"Edit tables written to {db_path}: {n_ptp:,} PTP rows, {n_mue:,} MUE rows ({meta})")
    return db_path
