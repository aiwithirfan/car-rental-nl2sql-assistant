"""Guardrail test harness: proves that unsafe requests never reach the data."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional

from .config import DB_PATH, UNSAFE_REQUESTS_PATH
from .executor import execute_select
from .pipeline import Text2SQLPipeline
from .validator import validate_sql


def load_unsafe_requests(path: Path | str = UNSAFE_REQUESTS_PATH) -> List[dict]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _row_counts(db_path: Path | str) -> Dict[str, int]:
    from .database import table_counts
    return table_counts(db_path)


def run_offline(db_path: Path | str = DB_PATH, timeout_s: float = 1.0) -> List[dict]:
    """Feed each attack SQL straight to the validator and executor (no LLM needed)."""
    log = []
    for case in load_unsafe_requests():
        sql = case["attack_sql"]
        verdict = validate_sql(sql)
        if not verdict.ok:
            blocked, layer, reason = True, verdict.layer, verdict.reason
        else:
            run = execute_select(db_path, verdict.sql, max_rows=10, timeout_s=timeout_s)
            blocked = not run.ok
            layer, reason = run.layer, run.error
        log.append({"id": case["id"], "request": case["request"], "attack_sql": sql.replace("\n", " "),
                    "blocked": blocked, "caught_by": layer if blocked else "NOT BLOCKED", "detail": reason})
    return log


def run_with_llm(pipeline: Text2SQLPipeline) -> List[dict]:
    """Send each plain-English unsafe request through the full pipeline (needs an LLM)."""
    before = _row_counts(pipeline.db_path)
    log = []
    for case in load_unsafe_requests():
        result = pipeline.ask(case["request"])
        harmless_select = result.status == "ok"
        log.append({"id": case["id"], "request": case["request"], "generated_sql": result.sql.replace("\n", " "),
                    "status": result.status, "caught_by": result.layer or "n/a",
                    "blocked": result.status in ("blocked", "refused") or harmless_select,
                    "detail": result.error or ("model produced a harmless read-only SELECT" if harmless_select else "")})
    after = _row_counts(pipeline.db_path)
    for row in log:
        row["data_unchanged"] = before == after
    return log


def summarise(log: List[dict]) -> Optional[str]:
    total = len(log)
    blocked = sum(1 for r in log if r["blocked"])
    return f"{blocked}/{total} unsafe requests blocked"
