"""Build the SQLite database: ``python scripts/build_db.py``."""
import _bootstrap  # noqa: F401
from car_rental_sql.database import build_database, table_counts

if __name__ == "__main__":
    path = build_database()
    counts = table_counts(path)
    print(f"Database written to {path}")
    for table, n in counts.items():
        print(f"  {table:<20}{n:>7}")
    print(f"  {'TOTAL':<20}{sum(counts.values()):>7}")
