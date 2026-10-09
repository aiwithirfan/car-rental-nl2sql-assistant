# Ablation study

**Rule for this project:** remove or swap one major component and explain precisely what the change costs.
Each variant changes *exactly one thing* relative to `baseline`; everything else (model, questions, scoring,
seed, "today" date) is identical.

| Variant | What changes | Command flag |
|---|---|---|
| `baseline` | Full schema prompt (descriptions, foreign keys, 3 sample rows, business rules) + up to 2 error retries | - |
| `no_retry` | **Removes the error-retry loop** (`max_retries = 0`) | `run_ablation.py` |
| `schema_ddl_only` | **Swaps** the full prompt for raw `CREATE TABLE` statements (no descriptions, samples or business rules) | `run_ablation.py` |
| `schema_tables_only` | **Swaps** it for a bare list of table names (starved baseline) | `run_ablation.py` |
| `model_swap` | **Swaps** the model for a cheaper one (`--alt-model`) | `run_ablation.py --alt-model <name>` |

Run everything with `python scripts/run_ablation.py --provider anthropic --alt-model claude-haiku-5-5`
and then `python scripts/make_report.py`.

## How to read the results
For every variant compare accuracy **per difficulty level** against `baseline`, then open
`results/eval_<variant>.csv` and read the failing rows:

* **`no_retry`** - expected cost: questions that the baseline fixed on the second attempt (mostly
  `hallucinated_column`, `syntax_error`, `ambiguous_column`). The number of such questions is
  `retries_used > 0` in `eval_baseline.csv`, which tells you the *exact* value of the retry loop.
* **`schema_ddl_only`** - expected cost: lost knowledge of enumerated values (`status = 'completed'`,
  `loyalty_tier = 'Gold'`), the rental-length and "late/overdue" definitions, and the ambiguous `name`
  column. Look for `wrong_filter` and `wrong_value_or_aggregation`.
* **`schema_tables_only`** - expected cost: the model must guess column names, so `hallucinated_column`
  dominates; the retry loop partially rescues it because the error message names the bad column.
* **`model_swap`** - cost split by difficulty; hard questions (window functions, correlated subqueries) are
  usually where a smaller model drops first.

The write-up of the real numbers (what you observed, not these expectations) goes into the README results
block and the video.
