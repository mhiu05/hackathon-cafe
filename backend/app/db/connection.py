"""SQLite connection factory with the project-wide PRAGMAs and explicit transactions.

Every connection (pipeline scripts, FastAPI requests, agent tools) MUST be created here so that
foreign keys, WAL and busy_timeout are always on. Connections run in autocommit mode
(isolation_level=None); multi-statement writes MUST use `transaction(conn)`.
"""
from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

BUSY_TIMEOUT_MS = 5000


def connect(db_path: Path | str, *, read_only: bool = False) -> sqlite3.Connection:
    """Open a connection with row factory, FK enforcement, WAL and busy timeout.

    `read_only=True` opens via URI mode=ro (used by retrieval/eval tooling).
    """
    path = Path(db_path)
    if read_only:
        conn = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True, check_same_thread=False, isolation_level=None)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute(f"PRAGMA busy_timeout = {BUSY_TIMEOUT_MS}")
    if not read_only:
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
    return conn


@contextmanager
def transaction(conn: sqlite3.Connection, *, immediate: bool = True) -> Iterator[sqlite3.Connection]:
    """BEGIN [IMMEDIATE] ... COMMIT, ROLLBACK on any exception.

    IMMEDIATE takes the write lock up front so concurrent writers wait (busy_timeout) instead of failing mid-transaction.
    """
    conn.execute("BEGIN IMMEDIATE" if immediate else "BEGIN")
    try:
        yield conn
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    else:
        conn.execute("COMMIT")
