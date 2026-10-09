"""Run the 50-question benchmark for one configuration.

Example:  python scripts/run_eval.py --provider anthropic --variant baseline
"""
import argparse

import pandas as pd

import _bootstrap  # noqa: F401
from _cli import add_llm_args, build_llm
from car_rental_sql.config import RESULTS_DIR, PipelineConfig
from car_rental_sql.evaluate import load_questions, run_evaluation

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    add_llm_args(parser)
    parser.add_argument("--variant", default="baseline", help="Name used in the results file.")
    parser.add_argument("--schema-mode", default="full", choices=["full", "ddl", "tables"])
    parser.add_argument("--max-retries", type=int, default=2)
    parser.add_argument("--limit", type=int, default=None, help="Only run the first N questions (smoke test).")
    args = parser.parse_args()

    llm = build_llm(args)
    questions = load_questions()[: args.limit] if args.limit else None
    config = PipelineConfig(schema_mode=args.schema_mode, max_retries=args.max_retries)

    def show(i, n, rec):
        mark = "OK " if rec["correct"] else "ERR"
        print(f"[{i:>2}/{n}] {mark} {rec['question_id']} ({rec['difficulty']}) {rec['failure_type']}")

    records = run_evaluation(llm, config, args.variant, questions=questions, progress=show)
    df = pd.DataFrame(records)
    RESULTS_DIR.mkdir(exist_ok=True)
    out = RESULTS_DIR / f"eval_{args.variant}.csv"
    df.to_csv(out, index=False)
    print(f"\nExecution accuracy: {df['correct'].mean():.1%} ({int(df['correct'].sum())}/{len(df)})")
    print(df.groupby("difficulty")["correct"].mean().map("{:.1%}".format).to_string())
    print(f"Saved {out}")
