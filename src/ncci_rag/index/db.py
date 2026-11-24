"""A SQLite connection that several threads can share safely.

Streamlit runs every rerun of the script, and every visitor's session, on its own
thread, while the pipeline (and its open SQLite files) is created once and cached. A
plain ``sqlite3`` connection refuses use from another thread, and with
``check_same_thread=False`` two threads must still not use it at the same time.

So every statement here runs under one lock and returns all of its rows before the lock
is released: no cursor is ever left open for another thread to step on. The files are
small and the queries take microseconds, so the lock costs nothing measurable.
"""

from __future__ import annotations

import sqlite3
import threading
from pathlib import Path


class Rows(list):
    """Query result: a list, plus ``fetchone``/``fetchall`` for code written against cursors."""

    def fetchone(self):
        return self[0] if self else None

    def fetchall(self):
        return list(self)


class SharedConnection:
    def __init__(self, path: str | Path):
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        self._lock = threading.Lock()

    def execute(self, sql: str, params: tuple | list = ()) -> Rows:
        with self._lock:
            return Rows(self._conn.execute(sql, params).fetchall())

    def commit(self) -> None:
        with self._lock:
            self._conn.commit()

    def close(self) -> None:
        with self._lock:
            self._conn.close()
