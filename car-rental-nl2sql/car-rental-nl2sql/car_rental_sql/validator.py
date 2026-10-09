"""Read-only SQL validator (guardrail layer 1).

The validator is deliberately conservative. It first *tokenises* the query so that
comments and quoted text can never hide a keyword or a second statement, then
applies a short list of rules. Everything that passes is returned as ``sql`` in a
cleaned form (comments removed) - that cleaned string is what gets executed, so the
text that was validated is exactly the text that runs.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

MAX_SQL_LENGTH = 5000

BLOCKED_KEYWORDS = (
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "TRUNCATE", "ATTACH", "DETACH",
    "PRAGMA", "VACUUM", "REINDEX", "ANALYZE", "BEGIN", "COMMIT", "ROLLBACK", "SAVEPOINT",
    "RELEASE", "EXPLAIN", "GRANT", "REVOKE", "EXEC", "EXECUTE", "UPSERT",
)
_BLOCKED_RE = re.compile(r"\b(" + "|".join(BLOCKED_KEYWORDS) + r")\b", re.IGNORECASE)
_REPLACE_INTO_RE = re.compile(r"\bREPLACE\s+INTO\b", re.IGNORECASE)
_FIRST_WORD_RE = re.compile(r"^\s*([A-Za-z]+)")


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    sql: str = ""
    layer: Optional[str] = None
    reason: str = ""


class _ScanError(ValueError):
    pass


def _scan(sql: str):
    """Return (clean, masked): comments removed; ``masked`` also blanks quoted text."""
    clean, masked = [], []
    i, n = 0, len(sql)
    while i < n:
        ch = sql[i]
        if sql.startswith("--", i):
            j = sql.find("\n", i)
            i = n if j == -1 else j
            clean.append(" ")
            masked.append(" ")
            continue
        if sql.startswith("/*", i):
            j = sql.find("*/", i + 2)
            if j == -1:
                raise _ScanError("unterminated comment")
            i = j + 2
            clean.append(" ")
            masked.append(" ")
            continue
        if ch in ("'", '"', "`"):
            j = i + 1
            while True:
                if j >= n:
                    raise _ScanError("unterminated quoted text")
                if sql[j] == ch:
                    if j + 1 < n and sql[j + 1] == ch:  # doubled quote = escaped quote
                        j += 2
                        continue
                    break
                j += 1
            clean.append(sql[i : j + 1])
            masked.append(ch + ch)
            i = j + 1
            continue
        if ch == "[":
            j = sql.find("]", i + 1)
            if j == -1:
                raise _ScanError("unterminated [identifier]")
            clean.append(sql[i : j + 1])
            masked.append("[]")
            i = j + 1
            continue
        clean.append(ch)
        masked.append(ch)
        i += 1
    return "".join(clean), "".join(masked)


def validate_sql(sql: str) -> ValidationResult:
    """Check that ``sql`` is a single, read-only SELECT statement."""
    if sql is None or not str(sql).strip():
        return ValidationResult(False, layer="validator:empty", reason="Empty query.")
    sql = str(sql)
    if len(sql) > MAX_SQL_LENGTH:
        return ValidationResult(False, layer="validator:length", reason=f"Query longer than {MAX_SQL_LENGTH} characters.")
    if "\x00" in sql:
        return ValidationResult(False, layer="validator:syntax", reason="Query contains a null byte.")
    try:
        clean, masked = _scan(sql)
    except _ScanError as exc:
        return ValidationResult(False, layer="validator:syntax", reason=f"Malformed query: {exc}.")

    clean = clean.strip()
    masked = masked.strip()
    while masked.endswith(";"):  # a single trailing semicolon is harmless
        masked = masked[:-1].rstrip()
        clean = clean[:-1].rstrip()
    if not masked:
        return ValidationResult(False, layer="validator:empty", reason="Empty query.")

    if ";" in masked:
        return ValidationResult(False, layer="validator:multi_statement",
                                reason="Only one SQL statement is allowed.")

    match = _FIRST_WORD_RE.match(masked)
    first = match.group(1).upper() if match else ""
    if first not in ("SELECT", "WITH"):
        return ValidationResult(False, layer="validator:statement_type",
                                reason=f"Only SELECT queries are allowed (got '{first or masked[:12]}').")

    keyword = _BLOCKED_RE.search(masked)
    if keyword:
        return ValidationResult(False, layer="validator:keyword",
                                reason=f"Forbidden keyword '{keyword.group(1).upper()}' - the assistant is read-only.")
    if _REPLACE_INTO_RE.search(masked):
        return ValidationResult(False, layer="validator:keyword", reason="Forbidden statement 'REPLACE INTO'.")

    lowered = clean.lower()
    if "sqlite_" in lowered:
        return ValidationResult(False, layer="validator:system_table",
                                reason="Access to SQLite system tables is not allowed.")
    if "load_extension" in lowered:
        return ValidationResult(False, layer="validator:keyword", reason="load_extension() is not allowed.")

    return ValidationResult(True, sql=clean)
