"""Helpers that turn evaluation CSVs into tables (shared by the report script and the app)."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd

from .config import RESULTS_DIR

ORDER = ["easy", "medium", "hard"]


def load_results(results_dir: Path | str = RESULTS_DIR) -> Optional[pd.DataFrame]:
    files = sorted(Path(results_dir).glob("eval_*.csv"))
    if not files:
        return None
    return pd.concat([pd.read_csv(f) for f in files], ignore_index=True)


def accuracy_by_difficulty(df: pd.DataFrame) -> pd.DataFrame:
    """Rows = variant, columns = easy/medium/hard/overall, values = accuracy in %."""
    by_level = df.pivot_table(index="variant", columns="difficulty", values="correct", aggfunc="mean") * 100
    by_level = by_level.reindex(columns=[c for c in ORDER if c in by_level.columns])
    by_level["overall"] = df.groupby("variant")["correct"].mean() * 100
    return by_level.round(1)


def counts_by_difficulty(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby(["variant", "difficulty"])["correct"].agg(["sum", "count"]).reset_index()
    g["score"] = g["sum"].astype(int).astype(str) + "/" + g["count"].astype(str)
    out = g.pivot(index="variant", columns="difficulty", values="score")
    return out.reindex(columns=[c for c in ORDER if c in out.columns])


def failure_breakdown(df: pd.DataFrame) -> pd.DataFrame:
    wrong = df[df["correct"] == 0].copy()
    wrong["failure_type"] = wrong["failure_type"].fillna("unclassified")
    return wrong.pivot_table(index="failure_type", columns="variant", values="question_id",
                             aggfunc="count", fill_value=0)


def markdown_table(df: pd.DataFrame, index_label: str = "variant") -> str:
    cols = [index_label] + [str(c) for c in df.columns]
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join(["---"] * len(cols)) + "|"]
    for idx, row in df.iterrows():
        lines.append("| " + " | ".join([str(idx)] + [str(v) for v in row.tolist()]) + " |")
    return "\n".join(lines)
