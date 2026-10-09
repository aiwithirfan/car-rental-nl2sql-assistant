"""Builds the schema section of the prompt in three levels of richness.

``full``    - tables, typed columns with descriptions, foreign keys, sample rows, business rules
``ddl``     - only the raw CREATE TABLE statements (what a developer would paste)
``tables``  - only the table names (a deliberately starved baseline for the ablation)
"""
from __future__ import annotations

import sqlite3
from typing import List

from .config import CURRENCY, REFERENCE_DATE, SCHEMA_MODES, TABLES
from .schema import BUSINESS_NOTES, COLUMN_DOCS, TABLE_DOCS

SAMPLE_ROWS = 3


def _ddl_prompt(conn: sqlite3.Connection) -> str:
    rows = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY rowid"
    ).fetchall()
    return "\n\n".join(r[0].strip() + ";" for r in rows if r[0])


def _tables_prompt() -> str:
    return "Tables: " + ", ".join(TABLES)


def _full_prompt(conn: sqlite3.Connection) -> str:
    parts: List[str] = [
        f"SQLite database of a car rental company. Money is in {CURRENCY}. Today's date is {REFERENCE_DATE}.",
        "",
    ]
    for table in TABLES:
        info = conn.execute(f"PRAGMA table_info({table})").fetchall()
        fks = {fk[3]: f"{fk[2]}.{fk[4]}" for fk in conn.execute(f"PRAGMA foreign_key_list({table})").fetchall()}
        parts.append(f"TABLE {table} - {TABLE_DOCS[table]}")
        for _cid, name, ctype, _notnull, _default, pk in info:
            doc = COLUMN_DOCS[table].get(name, "")
            flags = " PRIMARY KEY" if pk else ""
            if name in fks:
                flags += f" -> {fks[name]}"
            parts.append(f"  - {name} ({ctype}{flags}): {doc}")
        sample = conn.execute(f"SELECT * FROM {table} LIMIT {SAMPLE_ROWS}").fetchall()
        col_names = [c[1] for c in info]
        parts.append(f"  sample rows ({', '.join(col_names)}):")
        for row in sample:
            parts.append("    " + str(tuple(row)))
        parts.append("")
    parts.append(BUSINESS_NOTES)
    return "\n".join(parts)


def build_schema_prompt(conn: sqlite3.Connection, mode: str = "full") -> str:
    if mode not in SCHEMA_MODES:
        raise ValueError(f"Unknown schema mode '{mode}'. Choose from {SCHEMA_MODES}.")
    if mode == "full":
        return _full_prompt(conn)
    if mode == "ddl":
        return _ddl_prompt(conn)
    return _tables_prompt()
