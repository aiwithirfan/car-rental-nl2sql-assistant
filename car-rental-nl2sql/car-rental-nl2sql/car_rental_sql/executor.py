"""Safe query execution (guardrail layers 2-4).

Defence in depth - even if the validator had a bug, a query still has to get past:
  * a connection opened in ``mode=ro`` (the OS-level file is read-only for SQLite),
  * ``PRAGMA query_only = ON``,
  * an SQLite *authorizer* that only permits SELECT/READ on the known business tables,
  * a progress handler that aborts anything running longer than ``timeout_s``,
  * a hard cap on the number of rows fetched.
"""
from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Sequence

from .config import DEFAULT_MAX_ROWS, DEFAULT_TIMEOUT_S, TABLES

# Numeric values of the SQLite authorizer action codes / return codes.
_OK, _DENY = 0, 1
_READ, _SELECT, _FUNCTION, _RECURSIVE = 20, 21, 31, 33
_DENIED_FUNCTIONS = {"load_extension"}


@dataclass
class ExecutionResult:
    ok: bool
    columns: List[str] = field(default_factory=list)
    rows: List[tuple] = field(default_factory=list)
    truncated: bool = False
    error: str = ""
    layer: Optional[str] = None  # which guardrail / failure type: timeout, authorizer, readonly, sql_error
    elapsed_s: float = 0.0


def connect_readonly(db_path: Path | str) -> sqlite3.Connection:
    """Open the database in read-only mode."""
    uri = f"{Path(db_path).resolve().as_uri()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True, check_same_thread=False)
    conn.execute("PRAGMA query_only = ON")
    return conn


def _make_authorizer(allowed_tables: Sequence[str]):
    allowed = {t.lower() for t in allowed_tables}

    def authorizer(action, arg1, arg2, _db, _source):
        if action in (_SELECT, _RECURSIVE):
            return _OK
        if action == _READ:
            return _OK if (arg1 or "").lower() in allowed else _DENY
        if action == _FUNCTION:
            return _DENY if (arg2 or "").lower() in _DENIED_FUNCTIONS else _OK
        return _DENY

    return authorizer


def execute_select(
    db_path: Path | str,
    sql: str,
    max_rows: int = DEFAULT_MAX_ROWS,
    timeout_s: float = DEFAULT_TIMEOUT_S,
    allowed_tables: Sequence[str] = TABLES,
) -> ExecutionResult:
    """Run an already-validated SELECT with all runtime guardrails switched on."""
    started = time.monotonic()
    conn = connect_readonly(db_path)
    deadline = started + timeout_s
    conn.set_authorizer(_make_authorizer(allowed_tables))
    conn.set_progress_handler(lambda: 1 if time.monotonic() > deadline else 0, 10_000)
    try:
        cursor = conn.execute(sql)
        columns = [d[0] for d in cursor.description] if cursor.description else []
        fetched = cursor.fetchmany(max_rows + 1)
        truncated = len(fetched) > max_rows
        return ExecutionResult(True, columns, fetched[:max_rows], truncated,
                               elapsed_s=time.monotonic() - started)
    except sqlite3.Error as exc:
        message = str(exc)
        low = message.lower()
        if "interrupted" in low:
            layer, message = "timeout", f"Query exceeded the {timeout_s:g}s time limit."
        elif "not authorized" in low or "prohibited" in low:
            layer = "authorizer"
        elif "readonly" in low or "read-only" in low:
            layer = "readonly_connection"
        else:
            layer = "sql_error"
        return ExecutionResult(False, error=message, layer=layer, elapsed_s=time.monotonic() - started)
    finally:
        conn.close()
