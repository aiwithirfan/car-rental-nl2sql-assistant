from car_rental_sql.executor import connect_readonly, execute_select


def test_runs_select(db_path):
    run = execute_select(db_path, "SELECT COUNT(*) FROM customers")
    assert run.ok and run.rows == [(600,)]


def test_row_limit_truncates(db_path):
    run = execute_select(db_path, "SELECT * FROM rentals", max_rows=5)
    assert run.ok and len(run.rows) == 5 and run.truncated


def test_timeout(db_path):
    run = execute_select(db_path, "SELECT COUNT(*) FROM rentals a, rentals b, rentals c, payments d", timeout_s=0.5)
    assert not run.ok and run.layer == "timeout"


def test_authorizer_blocks_system_tables(db_path):
    run = execute_select(db_path, "SELECT * FROM sqlite_master")
    assert not run.ok and run.layer == "authorizer"


def test_authorizer_blocks_writes_even_if_validator_is_bypassed(db_path):
    run = execute_select(db_path, "DELETE FROM customers")
    assert not run.ok
    assert execute_select(db_path, "SELECT COUNT(*) FROM customers").rows == [(600,)]


def test_connection_is_read_only(db_path):
    conn = connect_readonly(db_path)
    try:
        import sqlite3
        try:
            conn.execute("DELETE FROM customers")
            raised = False
        except sqlite3.Error:
            raised = True
        assert raised
    finally:
        conn.close()


def test_sql_error_is_reported(db_path):
    run = execute_select(db_path, "SELECT nope FROM customers")
    assert not run.ok and run.layer == "sql_error" and "no such column" in run.error
