"""Execution-accuracy scoring: compare *result sets*, never SQL text."""
from __future__ import annotations

import itertools
import math
import re
from typing import List, Sequence, Tuple

from .config import TABLES
from .pipeline import tables_used

Row = Tuple


def _num(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _sort_key(v):
    if v is None:
        return (0, 0.0, "")
    if _num(v):
        return (1, round(float(v), 2), "")
    return (2, 0.0, str(v).strip().casefold())


def _close(a, b) -> bool:
    if a is None or b is None:
        return a is None and b is None
    if _num(a) and _num(b):
        return math.isclose(float(a), float(b), rel_tol=1e-4, abs_tol=0.011)
    return str(a).strip().casefold() == str(b).strip().casefold()


def _rows_close(a: Sequence[Row], b: Sequence[Row]) -> bool:
    if len(a) != len(b):
        return False
    ra = sorted(a, key=lambda r: tuple(_sort_key(v) for v in r))
    rb = sorted(b, key=lambda r: tuple(_sort_key(v) for v in r))
    return all(len(x) == len(y) and all(_close(p, q) for p, q in zip(x, y)) for x, y in zip(ra, rb))


def _column(rows: Sequence[Row], j: int) -> List:
    return sorted((r[j] for r in rows), key=_sort_key)


def _columns_close(a: List, b: List) -> bool:
    return len(a) == len(b) and all(_close(x, y) for x, y in zip(a, b))


def strict_match(gold: Sequence[Row], pred: Sequence[Row]) -> bool:
    """Same rows (order-insensitive), same columns in the same order."""
    if not gold and not pred:
        return True
    if len(gold) != len(pred) or len(gold[0]) != len(pred[0]):
        return False
    return _rows_close(gold, pred)


def lenient_match(gold: Sequence[Row], pred: Sequence[Row]) -> bool:
    """Like strict, but extra columns and a different column order are tolerated.

    Every gold column must be found among the predicted columns with the same values
    *and* the rows must line up, so a query returning the right numbers for the wrong
    entities still fails.
    """
    if strict_match(gold, pred):
        return True
    if not gold or not pred or len(gold) != len(pred):
        return False
    g_cols, p_cols = len(gold[0]), len(pred[0])
    if p_cols < g_cols:
        return False
    gold_columns = [_column(gold, j) for j in range(g_cols)]
    pred_columns = [_column(pred, k) for k in range(p_cols)]
    candidates = [[k for k in range(p_cols) if _columns_close(gold_columns[j], pred_columns[k])]
                  for j in range(g_cols)]
    if any(not c for c in candidates):
        return False
    for combo in itertools.islice(itertools.product(*candidates), 500):
        if len(set(combo)) != len(combo):
            continue
        projected = [tuple(r[k] for k in combo) for r in pred]
        if _rows_close(gold, projected):
            return True
    return False


def classify_failure(status: str, error: str, layer: str, gold_sql: str, pred_sql: str,
                     gold_rows: Sequence[Row], pred_rows: Sequence[Row]) -> str:
    """Heuristic failure label used for the error analysis (review a sample by hand)."""
    low = (error or "").lower()
    if status in ("blocked", "refused"):
        return "blocked_or_refused"
    if layer == "timeout":
        return "timeout"
    if status == "error" or (error and not pred_rows):
        if "no such column" in low:
            return "hallucinated_column"
        if "no such table" in low:
            return "hallucinated_table"
        if "syntax error" in low or "incomplete input" in low:
            return "syntax_error"
        if "ambiguous column" in low:
            return "ambiguous_column"
        if layer == "llm_error":
            return "llm_api_error"
        return "other_sql_error"
    if tables_used(gold_sql, TABLES) != tables_used(pred_sql, TABLES):
        return "wrong_join"
    if len(gold_rows) != len(pred_rows):
        return "wrong_filter"
    return "wrong_value_or_aggregation"
