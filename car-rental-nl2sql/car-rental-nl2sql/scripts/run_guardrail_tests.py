"""Run the unsafe-request tests.

Offline (no API key needed):  python scripts/run_guardrail_tests.py
With the LLM in the loop:     python scripts/run_guardrail_tests.py --with-llm --provider anthropic
"""
import argparse

import pandas as pd

import _bootstrap  # noqa: F401
from _cli import add_llm_args, build_llm
from car_rental_sql import guardrails
from car_rental_sql.config import RESULTS_DIR, PipelineConfig
from car_rental_sql.pipeline import Text2SQLPipeline

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    add_llm_args(parser)
    parser.add_argument("--with-llm", action="store_true")
    args = parser.parse_args()
    RESULTS_DIR.mkdir(exist_ok=True)

    if args.with_llm:
        log = guardrails.run_with_llm(Text2SQLPipeline(build_llm(args), config=PipelineConfig()))
        out = RESULTS_DIR / "guardrail_log_llm.csv"
    else:
        log = guardrails.run_offline()
        out = RESULTS_DIR / "guardrail_log_validator.csv"
    df = pd.DataFrame(log)
    df.to_csv(out, index=False)
    print(df[["id", "blocked", "caught_by"]].to_string(index=False))
    print(f"\n{guardrails.summarise(log)}  ->  {out}")
