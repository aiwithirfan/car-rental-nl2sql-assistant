from car_rental_sql.config import PipelineConfig
from car_rental_sql.pipeline import Text2SQLPipeline, extract_sql
from car_rental_sql.schema_prompt import build_schema_prompt
from car_rental_sql.executor import connect_readonly
from fakes import ScriptedLLM


def test_happy_path(db_path):
    llm = ScriptedLLM(["```sql\nSELECT COUNT(*) FROM customers\n```"])
    result = Text2SQLPipeline(llm, db_path).ask("How many customers?")
    assert result.status == "ok" and result.rows == [(600,)] and result.retries_used == 0


def test_retry_fixes_hallucinated_column(db_path):
    llm = ScriptedLLM(["SELECT full_name FROM customers", "SELECT first_name FROM customers LIMIT 1"])
    result = Text2SQLPipeline(llm, db_path, PipelineConfig(max_retries=2)).ask("names")
    assert result.status == "ok" and result.retries_used == 1
    assert "no such column" in llm.calls[1][-1]["content"]  # the error was fed back to the model


def test_no_retry_when_disabled(db_path):
    llm = ScriptedLLM(["SELECT full_name FROM customers"])
    result = Text2SQLPipeline(llm, db_path, PipelineConfig(max_retries=0)).ask("names")
    assert result.status == "error" and len(llm.calls) == 1


def test_retry_budget_is_respected(db_path):
    llm = ScriptedLLM(["SELECT a FROM customers"] * 3)
    result = Text2SQLPipeline(llm, db_path, PipelineConfig(max_retries=2)).ask("x")
    assert result.status == "error" and len(llm.calls) == 3


def test_unsafe_sql_is_blocked_and_never_retried(db_path):
    llm = ScriptedLLM(["DELETE FROM customers", "SELECT 1"])
    result = Text2SQLPipeline(llm, db_path).ask("delete all customers")
    assert result.status == "blocked" and len(llm.calls) == 1
    assert Text2SQLPipeline(ScriptedLLM(["SELECT COUNT(*) FROM customers"]), db_path).ask("c").rows == [(600,)]


def test_model_refusal(db_path):
    result = Text2SQLPipeline(ScriptedLLM(["REFUSE: this would modify data"]), db_path).ask("delete all customers")
    assert result.status == "refused" and result.layer == "llm_refusal"


def test_empty_question(db_path):
    assert Text2SQLPipeline(ScriptedLLM([]), db_path).ask("  ").status == "error"


def test_extract_sql_variants():
    assert extract_sql("```sql\nSELECT 1\n```") == ("sql", "SELECT 1")
    assert extract_sql("Sure! SELECT 2")[1] == "SELECT 2"
    assert extract_sql("REFUSE: no") == ("refuse", "no")
    assert extract_sql("DROP TABLE x") == ("sql", "DROP TABLE x")


def test_schema_modes(db_path):
    conn = connect_readonly(db_path)
    full, ddl, tables = (build_schema_prompt(conn, m) for m in ("full", "ddl", "tables"))
    conn.close()
    assert "sample rows" in full and "Business rules" in full
    assert "CREATE TABLE" in ddl and "sample rows" not in ddl
    assert tables.startswith("Tables:") and "CREATE" not in tables
    assert len(full) > len(ddl) > len(tables)
