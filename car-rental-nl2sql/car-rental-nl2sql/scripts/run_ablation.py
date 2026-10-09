"""Run the ablation study: the baseline plus variants that remove/swap one component.

Example:  python scripts/run_ablation.py --provider anthropic --alt-model claude-haiku-5-5
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
    parser.add_argument("--alt-model", default=None, help="Optional cheaper model for the 'model swap' variant.")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    questions = load_questions()[: args.limit] if args.limit else None
    variants = [
        ("baseline", PipelineConfig("full", 2), None),
        ("no_retry", PipelineConfig("full", 0), None),
        ("schema_ddl_only", PipelineConfig("ddl", 2), None),
        ("schema_tables_only", PipelineConfig("tables", 2), None),
    ]
    if args.alt_model:
        variants.append(("model_swap", PipelineConfig("full", 2), args.alt_model))

    RESULTS_DIR.mkdir(exist_ok=True)
    for name, config, model in variants:
        llm = build_llm(args, model)
        print(f"\n=== {name} ({llm.name}, schema={config.schema_mode}, retries={config.max_retries}) ===")
        records = run_evaluation(llm, config, name, questions=questions,
                                 progress=lambda i, n, r: print(f"  {i:>2}/{n} {'OK ' if r['correct'] else 'ERR'} {r['question_id']}"))
        df = pd.DataFrame(records)
        df.to_csv(RESULTS_DIR / f"eval_{name}.csv", index=False)
        print(f"  -> accuracy {df['correct'].mean():.1%}")
    print("\nNow run: python scripts/make_report.py")
