"""Makes ``import car_rental_sql`` work when a script is run as ``python scripts/xyz.py``."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
