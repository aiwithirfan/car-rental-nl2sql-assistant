"""Tests the evaluation harness itself with scripted 'models' (not a real accuracy measurement)."""
from car_rental_sql import guardrails
from car_rental_sql.config import PipelineConfig
from car_rental_sql.evaluate import load_questions, run_evaluation


class GoldOracle:
    """Returns the gold SQL for whatever question it is asked - proves scoring accepts a correct answer."""
    name = "oracle:test"

    def __init__(self):
        self.by_question = {q["question"]: q["gold_sql"] for q in load_questions()}

    def complete(self, system, messages):
        text = messages[0]["content"]
        question = text.split("<question>")[1].split("</question>")[0]
        return self.by_question[question]


class AlwaysWrong:
    name = "wrong:test"

    def complete(self, system, messages):
        return "SELECT COUNT(*) FROM vehicles"


def test_oracle_scores_100_percent(db_path):
    records = run_evaluation(GoldOracle(), PipelineConfig(), "oracle", db_path)
    assert len(records) == 50 and all(r["correct"] and r["strict_correct"] for r in records)


def test_wrong_model_scores_low_and_failures_are_labelled(db_path):
    records = run_evaluation(AlwaysWrong(), PipelineConfig(), "wrong", db_path, load_questions()[:15])
    assert sum(r["correct"] for r in records) <= 3
    assert all(r["failure_type"] for r in records if not r["correct"])


def test_offline_guardrails_block_everything(db_path):
    log = guardrails.run_offline(db_path)
    assert len(log) >= 10 and all(r["blocked"] for r in log)
