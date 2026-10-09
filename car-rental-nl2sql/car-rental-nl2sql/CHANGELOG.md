# Changelog

## 1.0.0 - Final submission build
- Added Streamlit app with Ask, Guardrail demo, Database and Evaluation tabs.
- Added ablation runner (`baseline`, `no_retry`, `schema_ddl_only`, `schema_tables_only`, `model_swap`) and report generator.
- Added 13-case unsafe-request log (offline + with-LLM modes).
- 58 pytest tests and a GitHub Actions workflow.
- Documentation: scope, plan, ablation, testing, summary, deployment.

## 0.4.0 - Validator and executor hardening
- **Tried:** keyword search on the raw SQL text. **Problem:** comments or quotes could hide keywords or a second statement. **Changed to:** a tokeniser that strips comments, masks quoted text and executes the cleaned SQL.
- Added SQLite authorizer (SELECT + business-table reads only), `mode=ro`, `PRAGMA query_only`, progress-handler timeout and a row cap.
- Decided never to retry a query that a safety layer rejected.

## 0.3.0 - Pipeline and scoring
- Prompt builder with three schema modes (`full`, `ddl`, `tables`) so the ablation changes one thing only.
- Retry loop feeds the SQLite error back to the model (max 2).
- Result-set scoring with numeric tolerance; lenient (extra columns allowed) and strict modes; heuristic failure labels.

## 0.2.0 - Question set
- 50 questions (15 easy, 20 medium, 15 hard) with gold SQL; all gold queries verified non-empty.
- Re-checked top-N questions for ties; switched money to whole-rupee integers so sums compare exactly.

## 0.1.0 - Database
- Seeded generator for 7 related tables (5,896 rows) with foreign-key check; data frozen at 2025-12-31.
- Added edge cases on purpose: never-rented vehicles, overdue active rentals, pending balances, one-way rentals.
