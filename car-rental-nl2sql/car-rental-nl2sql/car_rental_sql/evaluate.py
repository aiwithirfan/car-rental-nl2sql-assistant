"""Runs the 50-question benchmark and scores execution accuracy."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, List, Optional

from .config import DB_PATH, QUESTIONS_PATH, PipelineConfig
from .executor import execute_select
from .llm import LLMClient
from .pipeline import Text2SQLPipeline
from .scoring import classify_failure, lenient_match, strict_match

DIFFICULTIES = ("easy", "medium", "hard")


def load_questions(path: Path | str = QUESTIONS_PATH) -> List[dict]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def compute_gold(question: dict, db_path: Path | str = DB_PATH):
    run = execute_select(db_path, question["gold_sql"], max_rows=10_000, timeout_s=30)
    if not run.ok:
        raise RuntimeError(f"Gold SQL for {question['id']} failed: {run.error}")
    return run.columns, run.rows


def run_evaluation(llm: LLMClient, config: PipelineConfig, variant: str = "baseline",
                   db_path: Path | str = DB_PATH, questions: Optional[List[dict]] = None,
                   progress: Optional[Callable[[int, int, dict], None]] = None) -> List[dict]:
    questions = questions if questions is not None else load_questions()
    pipeline = Text2SQLPipeline(llm, db_path, config)
    records = []
    for i, q in enumerate(questions, start=1):
        _gold_cols, gold_rows = compute_gold(q, db_path)
        result = pipeline.ask(q["question"])
        correct = strict = False
        if result.status == "ok":
            strict = strict_match(gold_rows, result.rows)
            correct = lenient_match(gold_rows, result.rows)
        failure = "" if correct else classify_failure(result.status, result.error, result.layer or "",
                                                      q["gold_sql"], result.sql, gold_rows, result.rows)
        record = {
            "variant": variant, "model": llm.name, "schema_mode": config.schema_mode,
            "max_retries": config.max_retries, "question_id": q["id"], "difficulty": q["difficulty"],
            "question": q["question"], "status": result.status, "correct": int(correct),
            "strict_correct": int(strict), "failure_type": failure, "retries_used": result.retries_used,
            "latency_s": round(result.latency_s, 2), "predicted_sql": result.sql.replace("\n", " "),
            "gold_sql": q["gold_sql"], "error": (result.error or "").replace("\n", " "),
            "gold_rows": len(gold_rows), "pred_rows": len(result.rows),
        }
        records.append(record)
        if progress:
            progress(i, len(questions), record)
    return records
