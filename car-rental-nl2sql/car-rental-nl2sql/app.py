"""Streamlit front-end: ask the car rental database questions in plain English."""
from __future__ import annotations

import json
import os
import sqlite3

import pandas as pd
import streamlit as st

from car_rental_sql import __version__
from car_rental_sql.config import COMPANY_NAME, DB_PATH, QUESTIONS_PATH, REFERENCE_DATE, RESULTS_DIR, PipelineConfig
from car_rental_sql.database import ensure_database, table_counts
from car_rental_sql.executor import connect_readonly, execute_select
from car_rental_sql.llm import PROVIDER_PRESETS, LLMError, create_llm
from car_rental_sql.pipeline import Text2SQLPipeline
from car_rental_sql.reporting import accuracy_by_difficulty, failure_breakdown, load_results
from car_rental_sql.validator import validate_sql

st.set_page_config(page_title="Car Rental SQL Assistant", page_icon="🚗", layout="wide")

ensure_database(DB_PATH)

EXAMPLES = [
    "How many vehicles does each branch have?",
    "What is the total revenue from completed rentals for each pickup branch?",
    "Show the top 5 customers by total spend on completed rentals.",
    "Which active rentals are overdue?",
    "Which vehicle category earned the most revenue from completed rentals?",
    "Show each month of 2025 with its revenue and running total.",
]


def _secret(name: str) -> str | None:
    try:
        return st.secrets.get(name)  # type: ignore[no-any-return]
    except Exception:  # no secrets file present
        return None


def _dedupe(columns: list[str]) -> list[str]:
    seen: dict[str, int] = {}
    out = []
    for c in columns:
        seen[c] = seen.get(c, 0) + 1
        out.append(c if seen[c] == 1 else f"{c}_{seen[c]}")
    return out


@st.cache_data(show_spinner=False)
def _schema_overview() -> pd.DataFrame:
    conn = connect_readonly(DB_PATH)
    try:
        rows = []
        for table in table_counts(DB_PATH):
            for _cid, name, ctype, _nn, _d, pk in conn.execute(f"PRAGMA table_info({table})"):
                rows.append({"table": table, "column": name, "type": ctype, "primary key": bool(pk)})
        return pd.DataFrame(rows)
    finally:
        conn.close()


# ------------------------------------------------------------------ sidebar
with st.sidebar:
    st.title("🚗 Settings")
    provider = st.selectbox("LLM provider", list(PROVIDER_PRESETS),
                            format_func=lambda k: PROVIDER_PRESETS[k]["label"],
                            index=list(PROVIDER_PRESETS).index(_secret("LLM_PROVIDER") or "anthropic"))
    preset = PROVIDER_PRESETS[provider]
    model = st.text_input("Model", value=_secret("LLM_MODEL") or preset["default_model"],
                          help="Check your provider's documentation for the current model names.")
    base_url = None
    if provider == "custom":
        base_url = st.text_input("Base URL", value=os.environ.get("OPENAI_BASE_URL", "http://localhost:11434/v1"))
    key_default = _secret(preset["env_key"]) or os.environ.get(preset["env_key"]) or ""
    api_key = st.text_input("API key", type="password", value=key_default,
                            help="Never committed to GitHub. On Streamlit Cloud use Secrets instead.")
    st.divider()
    schema_mode = st.selectbox("Schema prompt", ["full", "ddl", "tables"],
                               help="full = descriptions + samples; ddl = CREATE statements; tables = names only.")
    max_retries = st.slider("Error-retry attempts", 0, 3, 2)
    max_rows = st.slider("Row limit", 10, 500, 200, step=10)
    timeout_s = st.slider("Query timeout (s)", 1, 15, 5)
    st.caption(f"v{__version__} · data frozen at {REFERENCE_DATE}")

st.title("Natural-Language-to-SQL Analytics Assistant")
st.caption(f"{COMPANY_NAME} · read-only guardrails · SQLite + LLM")

tab_ask, tab_guard, tab_db, tab_eval = st.tabs(["💬 Ask", "🛡️ Guardrail demo", "🗄️ Database", "📊 Evaluation"])

# ---------------------------------------------------------------------- ask
with tab_ask:
    chosen = st.selectbox("Try an example (or type your own below)", [""] + EXAMPLES)
    question = st.text_area("Your business question", value=chosen, height=90,
                            placeholder="e.g. Which branch had the most late returns?")
    if st.button("Run", type="primary", disabled=not question.strip()):
        try:
            llm = create_llm(provider, model, api_key or None, base_url)
        except LLMError as exc:
            st.error(str(exc))
        else:
            config = PipelineConfig(schema_mode, max_retries, max_rows, float(timeout_s))
            with st.spinner("Thinking..."):
                result = Text2SQLPipeline(llm, DB_PATH, config).ask(question)

            if result.status == "ok":
                c1, c2, c3 = st.columns(3)
                c1.metric("Rows", len(result.rows))
                c2.metric("Retries used", result.retries_used)
                c3.metric("Latency", f"{result.latency_s:.1f}s")
                st.subheader("Generated SQL")
                st.code(result.sql, language="sql")
                df = pd.DataFrame(result.rows, columns=_dedupe(result.columns))
                st.dataframe(df, use_container_width=True, hide_index=True)
                if result.truncated:
                    st.warning(f"Result truncated to the first {max_rows} rows.")
            elif result.status == "refused":
                st.warning(f"🛡️ Request refused by the model: {result.error}")
            elif result.status == "blocked":
                st.error(f"🛡️ Blocked by guardrail `{result.layer}`: {result.error}")
                if result.sql:
                    st.code(result.sql, language="sql")
            else:
                st.error(f"Could not answer this question: {result.error}")
                if result.sql:
                    st.code(result.sql, language="sql")

            with st.expander(f"Attempts ({len(result.attempts)})"):
                for i, a in enumerate(result.attempts, start=1):
                    st.markdown(f"**Attempt {i}** — `{a.status}`" + (f" · {a.layer}" if a.layer else ""))
                    if a.sql:
                        st.code(a.sql, language="sql")
                    if a.error:
                        st.caption(a.error)
    if not (api_key or _secret(preset["env_key"]) or provider == "custom"):
        st.info("Add an API key in the sidebar to enable the assistant. The other tabs work without one.")

# ----------------------------------------------------------------- guardrail
with tab_guard:
    st.write("Paste any SQL to see which guardrail layer stops it. No LLM is involved here.")
    default_sql = st.selectbox("Quick examples", [
        "SELECT COUNT(*) FROM customers",
        "DELETE FROM customers",
        "DROP TABLE rentals",
        "SELECT * FROM customers; DELETE FROM payments",
        "SELECT * FROM sqlite_master",
        "SELECT COUNT(*) FROM rentals a, rentals b, rentals c, payments d",
    ])
    sql_in = st.text_area("SQL", value=default_sql, height=100)
    if st.button("Check SQL"):
        verdict = validate_sql(sql_in)
        if not verdict.ok:
            st.error(f"Blocked by `{verdict.layer}` — {verdict.reason}")
        else:
            run = execute_select(DB_PATH, verdict.sql, max_rows=max_rows, timeout_s=min(float(timeout_s), 2.0))
            if run.ok:
                st.success("Passed the validator and executed read-only.")
                st.dataframe(pd.DataFrame(run.rows, columns=_dedupe(run.columns)), hide_index=True)
            else:
                st.error(f"Passed the validator but blocked at runtime by `{run.layer}` — {run.error}")
    log = RESULTS_DIR / "guardrail_log_validator.csv"
    if log.exists():
        st.subheader("Recorded guardrail test log")
        st.dataframe(pd.read_csv(log), hide_index=True, use_container_width=True)

# ----------------------------------------------------------------- database
with tab_db:
    counts = table_counts(DB_PATH)
    cols = st.columns(len(counts))
    for col, (table, n) in zip(cols, counts.items()):
        col.metric(table, f"{n:,}")
    st.caption(f"Total rows: {sum(counts.values()):,}")
    st.dataframe(_schema_overview(), hide_index=True, use_container_width=True)
    table = st.selectbox("Preview a table", list(counts))
    conn = connect_readonly(DB_PATH)
    try:
        st.dataframe(pd.read_sql_query(f"SELECT * FROM {table} LIMIT 20", conn), hide_index=True,
                     use_container_width=True)
    finally:
        conn.close()

# --------------------------------------------------------------- evaluation
with tab_eval:
    results = load_results()
    if results is None:
        st.info("No evaluation results yet. Run `python scripts/run_eval.py` and commit the files in `results/`.")
    else:
        st.subheader("Execution accuracy by difficulty (%)")
        acc = accuracy_by_difficulty(results)
        st.dataframe(acc, use_container_width=True)
        st.bar_chart(acc.drop(columns="overall").T)
        st.subheader("Failure types")
        st.dataframe(failure_breakdown(results), use_container_width=True)
    st.subheader("Question set")
    st.dataframe(pd.DataFrame(json.loads(QUESTIONS_PATH.read_text(encoding="utf-8")))[["id", "difficulty", "question"]],
                 hide_index=True, use_container_width=True)
