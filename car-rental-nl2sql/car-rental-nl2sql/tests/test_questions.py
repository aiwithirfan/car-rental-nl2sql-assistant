import json
from collections import Counter

from car_rental_sql.config import QUESTIONS_PATH, UNSAFE_REQUESTS_PATH
from car_rental_sql.evaluate import compute_gold
from car_rental_sql.validator import validate_sql

QUESTIONS = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))


def test_fifty_questions_with_rising_difficulty():
    assert len(QUESTIONS) == 50
    assert Counter(q["difficulty"] for q in QUESTIONS) == {"easy": 15, "medium": 20, "hard": 15}
    assert len({q["id"] for q in QUESTIONS}) == 50
    assert len({q["question"] for q in QUESTIONS}) == 50


def test_gold_sql_is_valid_and_non_trivial(db_path):
    for q in QUESTIONS:
        assert validate_sql(q["gold_sql"]).ok, q["id"]
        _cols, rows = compute_gold(q, db_path)
        assert rows, f"{q['id']} returns an empty result, which would make scoring meaningless"


def test_at_least_ten_unsafe_requests_and_validator_blocks_them():
    unsafe = json.loads(UNSAFE_REQUESTS_PATH.read_text(encoding="utf-8"))
    assert len(unsafe) >= 10
    for case in unsafe:
        if case["id"] == "U13":  # resource-exhaustion attempt: a valid SELECT, stopped by the timeout instead
            assert validate_sql(case["attack_sql"]).ok
        else:
            assert not validate_sql(case["attack_sql"]).ok, case["id"]
