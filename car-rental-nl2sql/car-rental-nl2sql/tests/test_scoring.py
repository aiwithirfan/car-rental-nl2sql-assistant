from car_rental_sql.scoring import classify_failure, lenient_match, strict_match

GOLD = [("Lahore", 10), ("Karachi", 20.0)]


def test_order_and_int_float_do_not_matter():
    assert strict_match(GOLD, [("Karachi", 20), ("Lahore", 10)])


def test_float_tolerance():
    assert strict_match([(1.0,)], [(1.004,)])
    assert not strict_match([(1.0,)], [(1.5,)])


def test_text_is_case_insensitive():
    assert strict_match([("Gold",)], [("gold",)])


def test_extra_and_reordered_columns_only_in_lenient():
    pred = [(10, "Lahore", 1), (20, "Karachi", 2)]
    assert not strict_match(GOLD, pred)
    assert lenient_match(GOLD, pred)


def test_wrong_values_fail_even_if_lenient():
    assert not lenient_match(GOLD, [("Lahore", 20), ("Karachi", 10)])
    assert not lenient_match(GOLD, [("Lahore", 10)])


def test_failure_labels():
    assert classify_failure("error", "no such column: x", "sql_error", "SELECT 1", "SELECT x", [], []) == "hallucinated_column"
    assert classify_failure("ok", "", "", "SELECT * FROM rentals JOIN customers", "SELECT * FROM rentals", [(1,)], [(1,)]) == "wrong_join"
    assert classify_failure("ok", "", "", "SELECT * FROM rentals", "SELECT * FROM rentals", [(1,), (2,)], [(1,)]) == "wrong_filter"
    assert classify_failure("blocked", "x", "validator:keyword", "", "", [], []) == "blocked_or_refused"
