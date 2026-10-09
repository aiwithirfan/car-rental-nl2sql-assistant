# Scope Statement - Family-Owned Car Rental Company

*Written before the build started; it fixed what the assistant must and must not do.*

## Business context
A family-owned car rental company operates **6 branches** (Lahore, Karachi, Islamabad, Faisalabad, Multan,
Peshawar) with a fleet of about **120 vehicles** in six categories (Economy, Compact, Sedan, SUV, Luxury, Van)
and roughly **600 registered customers**. Managers currently depend on a part-time analyst or spreadsheets for
every question about revenue, fleet use or late returns.

## Goal
Let a branch or operations manager ask a business question in plain English and get a correct, auditable
answer from the company database - without being able to change any data.

## In scope
* Read-only questions about: **customers, fleet, branches, rentals, payments, maintenance**.
* Typical questions: revenue per branch/category/month, fleet availability, late and overdue returns, top
  customers, outstanding payments, maintenance cost, one-way rentals, loyalty tiers.
* Showing the generated SQL next to every answer so a human can audit it.
* Single-turn questions in English.

## Out of scope
* Any write, schema change or administrative action (insert, update, delete, DDL, PRAGMA, ATTACH).
* Forecasting, recommendations, free-form chat, or advice not derivable from the tables.
* Multi-turn conversation memory, user accounts, per-user permissions.
* Live production data - the project uses a synthetic database frozen at **2025-12-31**.

## Data and assumptions
* SQLite, 7 related tables with foreign keys, at least 3,000 rows (actual: 5,896).
* Money is in PKR as whole numbers. "Today" is 2025-12-31 for all date logic.
* Rental length in days = `end_date - start_date`; a rental is *late* when `actual_return_date > end_date`.

## Success criteria
| Criterion | Target |
|---|---|
| Execution accuracy on 50 questions (result-set comparison) | at least 80% overall; easy questions at least 95% |
| Unsafe requests (13 tests) | 100% blocked, database unchanged |
| Every query | single SELECT, max 200 rows, max 5 s |
| Ablation | each removed component quantified per difficulty level |

## Risks considered
Prompt injection in the question text, hallucinated columns, silently wrong joins, runaway queries,
date ambiguity ("this month"), tie-breaking in top-N questions.
