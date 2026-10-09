# Testing and validation log

## Automated tests (`pytest`, 58 tests, no API key needed)
| File | What it proves |
|---|---|
| `test_validator.py` | 6 safe queries accepted; 18 unsafe/malformed ones rejected with the right layer (comment tricks, stacked statements, quoted `sqlite_master`, unterminated strings, null byte) |
| `test_executor.py` | row cap, 0.5 s timeout on a cross join, authorizer denies system tables, writes fail even if the validator is bypassed, connection is read-only |
| `test_database.py` | >= 4 tables, >= 3,000 rows, no FK violations, deterministic build, business invariants |
| `test_questions.py` | 50 questions (15/20/15), unique ids, every gold query valid and **non-empty**, 13 unsafe requests |
| `test_scoring.py` | order-insensitive, int/float tolerance, case-insensitive text, lenient vs strict, failure labels |
| `test_pipeline.py` | retry feeds the SQLite error back, retry budget respected, **no retry on blocked SQL**, model refusal, prompt modes |
| `test_evaluate_harness.py` | a scripted oracle scores 50/50 (scoring accepts correct answers) and a constant-wrong model scores low |
| `test_app.py` | Streamlit app boots without an API key |

## Problems found and fixed during the build
| # | Problem found | Fix |
|---|---|---|
| 1 | Money as floats would make "paid payments < total" (H10) depend on floating-point noise and unfairly penalise correct SQL | All money columns are whole-rupee integers; late fee is rounded |
| 2 | Top-N questions (M03, M07, M12, M19, H05, H15) could tie, making the gold answer arbitrary | Checked each for ties on the generated data; chose measures that are unique; fixed seed keeps it stable |
| 3 | Branch and category tables both have a column called `name` | Kept deliberately as a realistic hazard; the full prompt warns to qualify it, and `ambiguous_column` is a tracked failure type |
| 4 | A question for "never rented" vehicles (H02) and "overdue" rentals (H04) returned empty results on the first data draft | Generator now adds 4 brand-new vehicles with no rentals and ~5 overdue active rentals; a test enforces non-empty gold answers |
| 5 | Validator originally scanned raw text, so a keyword inside a comment or string could cause false alarms and a hidden `;` could slip through | Rewritten as a tokeniser that strips comments and masks quoted text before any rule runs; executes the cleaned text |
| 6 | `SELECT * FROM "sqlite_master"` hides the name from a masked scan | Added the system-table check on the unmasked text, and the authorizer independently denies it (verified separately) |
| 7 | A duplicated assignment of `return_branch` in the data generator | Removed the dead line (caught on review) |
| 8 | Weak unsafe-request test assertion (an `or` clause that could pass wrongly) | Rewritten to assert each case explicitly; U13 is the only expected pass-through and is stopped by the timeout |

## Manual review checklist for failures
1. Open `results/eval_<variant>.csv`, filter `correct == 0`.
2. For 5-10 failures compare `predicted_sql` with `gold_sql` and confirm the auto-label (`failure_type`).
3. If the model's answer is *defensible* (an ambiguous question), note it and, if needed, sharpen the question wording - never loosen the scorer silently.
