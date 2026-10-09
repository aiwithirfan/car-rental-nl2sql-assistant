import pytest

from car_rental_sql.validator import validate_sql


@pytest.mark.parametrize("sql", [
    "SELECT COUNT(*) FROM customers",
    "select * from vehicles;",
    "WITH t AS (SELECT 1 AS n) SELECT n FROM t",
    "SELECT replace(first_name, 'a', 'b') FROM customers",
    "SELECT 'DROP TABLE x' AS note",
    "SELECT first_name FROM customers -- trailing comment",
])
def test_allows_safe_queries(sql):
    assert validate_sql(sql).ok


@pytest.mark.parametrize("sql,layer", [
    ("", "validator:empty"),
    ("   ;  ", "validator:empty"),
    ("DELETE FROM customers", "validator:statement_type"),
    ("drop table rentals", "validator:statement_type"),
    ("UPDATE vehicles SET mileage = 0", "validator:statement_type"),
    ("INSERT INTO branches VALUES (9,'x','y','z','2020-01-01')", "validator:statement_type"),
    ("PRAGMA table_info(customers)", "validator:statement_type"),
    ("SELECT 1; SELECT 2", "validator:multi_statement"),
    ("SELECT 1; DROP TABLE customers", "validator:multi_statement"),
    ("SELECT 1 -- x\n; DROP TABLE customers", "validator:multi_statement"),
    ("WITH x AS (SELECT 1) DELETE FROM rentals", "validator:keyword"),
    ("SELECT * FROM customers WHERE 1=1 /* x */ ; DELETE FROM customers", "validator:multi_statement"),
    ("SELECT * FROM sqlite_master", "validator:system_table"),
    ('SELECT * FROM "sqlite_master"', "validator:system_table"),
    ("SELECT load_extension('evil')", "validator:keyword"),
    ("SELECT 'unterminated", "validator:syntax"),
    ("SELECT 1 /* unterminated", "validator:syntax"),
    ("SELECT 1\x00; DROP TABLE x", "validator:syntax"),
])
def test_blocks_unsafe_queries(sql, layer):
    result = validate_sql(sql)
    assert not result.ok
    assert result.layer == layer


def test_comments_are_stripped_from_executed_sql():
    result = validate_sql("SELECT 1 /* hidden */ -- note")
    assert result.ok and "hidden" not in result.sql and "note" not in result.sql


def test_length_limit():
    assert validate_sql("SELECT " + "1," * 3000 + "1").layer == "validator:length"
