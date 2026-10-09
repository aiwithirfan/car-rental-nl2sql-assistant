"""Execute every gold query and save the answers to questions/gold_answers.json."""
import json

import _bootstrap  # noqa: F401
from car_rental_sql.config import ROOT
from car_rental_sql.evaluate import compute_gold, load_questions

if __name__ == "__main__":
    out = {}
    for q in load_questions():
        cols, rows = compute_gold(q)
        out[q["id"]] = {"difficulty": q["difficulty"], "columns": cols, "row_count": len(rows),
                        "rows": [list(r) for r in rows[:25]]}
        print(f"{q['id']}: {len(rows)} row(s)")
    target = ROOT / "questions" / "gold_answers.json"
    target.write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    print(f"Saved {target}")
