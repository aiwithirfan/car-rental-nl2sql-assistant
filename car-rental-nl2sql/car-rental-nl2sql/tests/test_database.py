import sqlite3

from car_rental_sql.database import build_database, table_counts


def test_schema_size_and_integrity(db_path):
    counts = table_counts(db_path)
    assert len(counts) >= 4
    assert sum(counts.values()) >= 3000
    conn = sqlite3.connect(db_path)
    assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
    assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    conn.close()


def test_build_is_deterministic(tmp_path):
    a, b = build_database(tmp_path / "a.db", seed=7), build_database(tmp_path / "b.db", seed=7)
    q = "SELECT SUM(total_amount), COUNT(*) FROM rentals"
    assert sqlite3.connect(a).execute(q).fetchall() == sqlite3.connect(b).execute(q).fetchall()


def test_business_invariants(db_path):
    conn = sqlite3.connect(db_path)
    assert conn.execute("SELECT COUNT(*) FROM rentals WHERE end_date < start_date").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM rentals WHERE status='cancelled' AND total_amount <> 0").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM rentals WHERE start_date > '2025-12-31'").fetchone()[0] == 0
    conn.close()
