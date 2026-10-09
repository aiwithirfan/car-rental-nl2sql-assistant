"""Turn results/eval_*.csv into tables + charts and refresh the README results block."""
import re

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

import _bootstrap  # noqa: F401,E402
from car_rental_sql.config import RESULTS_DIR, ROOT  # noqa: E402
from car_rental_sql.reporting import (accuracy_by_difficulty, counts_by_difficulty, failure_breakdown,  # noqa: E402
                                      load_results, markdown_table)

START, END = "<!-- RESULTS:START -->", "<!-- RESULTS:END -->"

if __name__ == "__main__":
    df = load_results()
    if df is None:
        raise SystemExit("No results/eval_*.csv files found. Run scripts/run_eval.py or run_ablation.py first.")
    acc = accuracy_by_difficulty(df)
    counts = counts_by_difficulty(df)
    fails = failure_breakdown(df)

    order = [v for v in ["baseline", "no_retry", "schema_ddl_only", "schema_tables_only", "model_swap"] if v in acc.index]
    order += [v for v in acc.index if v not in order]
    acc = acc.loc[order]

    ax = acc.drop(columns="overall").plot(kind="bar", figsize=(9, 5), rot=20, width=0.8)
    ax.set_ylabel("Execution accuracy (%)")
    ax.set_xlabel("")
    ax.set_ylim(0, 105)
    ax.set_title("Execution accuracy by difficulty and ablation variant")
    ax.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    chart = RESULTS_DIR / "accuracy_by_difficulty.png"
    plt.savefig(chart, dpi=150)

    table_md = markdown_table(acc.assign(**{c: acc[c].map("{:.1f}%".format) for c in acc.columns}))
    counts_md = markdown_table(counts)
    fails_md = markdown_table(fails, "failure type") if len(fails) else "_No failures recorded._"
    (RESULTS_DIR / "accuracy_table.md").write_text(table_md + "\n", encoding="utf-8")
    (RESULTS_DIR / "failure_breakdown.md").write_text(fails_md + "\n", encoding="utf-8")

    block = (f"{START}\n### Execution accuracy (50 questions, result-set comparison)\n\n{table_md}\n\n"
             f"Correct answers out of total per level:\n\n{counts_md}\n\n"
             f"![Accuracy by difficulty](results/accuracy_by_difficulty.png)\n\n"
             f"### Failure analysis (questions answered wrongly)\n\n{fails_md}\n{END}")
    readme = ROOT / "README.md"
    text = readme.read_text(encoding="utf-8")
    if START in text and END in text:
        text = re.sub(re.escape(START) + r".*?" + re.escape(END), lambda _m: block, text, flags=re.DOTALL)
        readme.write_text(text, encoding="utf-8")
        print("README results block updated.")
    print(table_md)
    print(f"Chart saved to {chart}")
