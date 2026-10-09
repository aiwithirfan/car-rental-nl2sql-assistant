"""Central configuration: paths, constants and the pipeline settings dataclass."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "car_rental.db"
QUESTIONS_PATH = ROOT / "questions" / "questions.json"
UNSAFE_REQUESTS_PATH = ROOT / "questions" / "unsafe_requests.json"
RESULTS_DIR = ROOT / "results"
CACHE_DIR = ROOT / ".cache"

COMPANY_NAME = "Family-Owned Car Rental Company"
CURRENCY = "PKR"
# The data set is frozen at this date so that "today", "last month" etc. have
# one reproducible meaning and the gold answers never drift.
REFERENCE_DATE = "2025-12-31"
SEED = 42

TABLES = (
    "branches",
    "customers",
    "vehicle_categories",
    "vehicles",
    "rentals",
    "payments",
    "maintenance",
)

DEFAULT_MAX_ROWS = 200
DEFAULT_TIMEOUT_S = 5.0
DEFAULT_MAX_RETRIES = 2

SCHEMA_MODES = ("full", "ddl", "tables")


@dataclass(frozen=True)
class PipelineConfig:
    """Tunable settings of the text-to-SQL pipeline (also the ablation knobs)."""

    schema_mode: str = "full"  # full | ddl | tables
    max_retries: int = DEFAULT_MAX_RETRIES  # 0 disables the error-retry loop
    max_rows: int = DEFAULT_MAX_ROWS
    timeout_s: float = DEFAULT_TIMEOUT_S

    def __post_init__(self) -> None:
        if self.schema_mode not in SCHEMA_MODES:
            raise ValueError(f"schema_mode must be one of {SCHEMA_MODES}")
        if self.max_retries < 0:
            raise ValueError("max_retries must be >= 0")
        if self.max_rows < 1:
            raise ValueError("max_rows must be >= 1")
        if self.timeout_s <= 0:
            raise ValueError("timeout_s must be > 0")
