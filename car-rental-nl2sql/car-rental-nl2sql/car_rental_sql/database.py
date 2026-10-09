"""Builds the synthetic car rental database deterministically (seeded)."""
from __future__ import annotations

import random
import sqlite3
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, List, Tuple

from .config import DB_PATH, REFERENCE_DATE, SEED, TABLES
from .schema import DDL

REF = date.fromisoformat(REFERENCE_DATE)
DATA_START = date(2023, 1, 1)

BRANCHES = [
    (1, "Lahore Gulberg", "Lahore", "+92-42-3555-0101", "2015-03-10"),
    (2, "Karachi Clifton", "Karachi", "+92-21-3555-0102", "2016-07-22"),
    (3, "Islamabad F-7", "Islamabad", "+92-51-3555-0103", "2018-01-15"),
    (4, "Faisalabad Central", "Faisalabad", "+92-41-3555-0104", "2019-05-30"),
    (5, "Multan Cantt", "Multan", "+92-61-3555-0105", "2020-09-12"),
    (6, "Peshawar Saddar", "Peshawar", "+92-91-3555-0106", "2021-11-01"),
]
BRANCH_WEIGHTS = [26, 24, 20, 12, 10, 8]

CATEGORIES = [
    (1, "Economy", 5000, 4),
    (2, "Compact", 6500, 5),
    (3, "Sedan", 8500, 5),
    (4, "SUV", 14000, 7),
    (5, "Luxury", 25000, 5),
    (6, "Van", 12000, 12),
]
FLEET_PER_CATEGORY = {1: 30, 2: 24, 3: 30, 4: 20, 5: 8, 6: 8}  # 120 vehicles
PRICE_BAND = {
    1: (2_500_000, 3_500_000),
    2: (3_500_000, 4_500_000),
    3: (5_500_000, 8_000_000),
    4: (9_000_000, 14_000_000),
    5: (20_000_000, 35_000_000),
    6: (6_000_000, 9_000_000),
}
MODELS = {
    1: [("Suzuki", "Alto"), ("Suzuki", "Cultus"), ("Toyota", "Vitz"), ("Suzuki", "Wagon R")],
    2: [("Suzuki", "Swift"), ("Toyota", "Yaris"), ("KIA", "Picanto"), ("Honda", "Fit")],
    3: [("Toyota", "Corolla"), ("Honda", "Civic"), ("Hyundai", "Elantra"), ("Honda", "City")],
    4: [("Toyota", "Fortuner"), ("KIA", "Sportage"), ("Hyundai", "Tucson"), ("Honda", "BR-V")],
    5: [("Mercedes-Benz", "E-Class"), ("BMW", "5 Series"), ("Audi", "A6"), ("Toyota", "Land Cruiser")],
    6: [("Toyota", "HiAce"), ("Hyundai", "H-1"), ("Suzuki", "Bolan")],
}

FIRST_NAMES = [
    "Ahmed", "Ali", "Hassan", "Hussain", "Usman", "Bilal", "Hamza", "Zain", "Faisal", "Imran",
    "Kamran", "Naveed", "Omer", "Saad", "Talha", "Waqas", "Yasir", "Zubair", "Adnan", "Danish",
    "Ayesha", "Fatima", "Sana", "Hina", "Maryam", "Nida", "Zainab", "Amna", "Iqra", "Rabia",
    "Sadia", "Khadija", "Mahnoor", "Laiba", "Noor", "Areeba", "Bushra", "Farah", "Huma", "Saima",
]
LAST_NAMES = [
    "Khan", "Malik", "Sheikh", "Butt", "Chaudhry", "Qureshi", "Siddiqui", "Raza", "Mirza", "Abbasi",
    "Ansari", "Baig", "Dar", "Gill", "Hashmi", "Javed", "Lodhi", "Niazi", "Rana", "Shah",
    "Tariq", "Yousaf", "Zaidi", "Cheema", "Bhatti", "Awan", "Rehman", "Iqbal", "Akhtar", "Farooq",
]
SERVICE_TYPES = {
    "oil_change": (4_000, 9_000, 30),
    "inspection": (3_000, 8_000, 20),
    "brake_service": (15_000, 45_000, 12),
    "tire_replacement": (40_000, 90_000, 10),
    "repair": (20_000, 250_000, 15),
    "detailing": (2_000, 6_000, 13),
}
RATE_FACTOR = {2023: 0.85, 2024: 0.93, 2025: 1.0}
LATE_FEE_RATE = 0.5  # of the daily rate, per late day


def _iso(d: date) -> str:
    return d.isoformat()


def _rand_date(rng: random.Random, start: date, end: date) -> date:
    return start + timedelta(days=rng.randint(0, max(0, (end - start).days)))


def build_database(path: Path | str = DB_PATH, seed: int = SEED) -> Path:
    """Create (or overwrite) the SQLite database and return its path."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    rng = random.Random(seed)

    # ---------------------------------------------------------------- customers
    n_customers = 600
    cities = [b[2] for b in BRANCHES]
    customers: List[dict] = []
    used_emails, used_licences = set(), set()
    for cid in range(1, n_customers + 1):
        first, last = rng.choice(FIRST_NAMES), rng.choice(LAST_NAMES)
        email = f"{first}.{last}{cid}@example.com".lower()
        licence = f"DL-{rng.randint(1_000_000, 9_999_999)}"
        while licence in used_licences:
            licence = f"DL-{rng.randint(1_000_000, 9_999_999)}"
        used_emails.add(email)
        used_licences.add(licence)
        customers.append(
            {
                "customer_id": cid,
                "first_name": first,
                "last_name": last,
                "email": email,
                "phone": f"+92-3{rng.randint(0, 4)}{rng.randint(0, 9)}-{rng.randint(1_000_000, 9_999_999)}",
                "city": rng.choices(cities, weights=BRANCH_WEIGHTS)[0],
                "license_number": licence,
                "birth_date": _iso(_rand_date(rng, date(1960, 1, 1), date(2004, 12, 31))),
                "date_joined": _iso(_rand_date(rng, date(2021, 1, 1), date(2025, 11, 30))),
                "loyalty_tier": "Bronze",
            }
        )
    cust_weights = [rng.paretovariate(1.6) for _ in customers]

    # ----------------------------------------------------------------- vehicles
    vehicles: List[dict] = []
    vid = 0
    cat_rate = {c[0]: c[2] for c in CATEGORIES}
    for cat_id, count in FLEET_PER_CATEGORY.items():
        for _ in range(count):
            vid += 1
            make, model = rng.choice(MODELS[cat_id])
            year = rng.randint(2018, 2025)
            acquired = _rand_date(rng, date(max(year, 2022), 1, 1), date(2025, 6, 30))
            vehicles.append(
                {
                    "vehicle_id": vid,
                    "make": make,
                    "model": model,
                    "year": year,
                    "category_id": cat_id,
                    "branch_id": rng.choices([b[0] for b in BRANCHES], weights=BRANCH_WEIGHTS)[0],
                    "acquired": acquired,
                    "purchase_price": round(rng.randint(*PRICE_BAND[cat_id]), -4),
                    "never_rented": False,
                    "retired_on": None,
                }
            )
    rng.shuffle(vehicles)
    for i, v in enumerate(vehicles, start=1):  # re-number after shuffle
        v["vehicle_id"] = i
    # four brand-new vehicles added in December 2025 that have no rentals yet
    for v in vehicles[:4]:
        v["year"] = 2025
        v["acquired"] = date(2025, 12, rng.randint(5, 20))
        v["never_rented"] = True
    # six vehicles retired in early 2025
    for v in vehicles[4:10]:
        v["retired_on"] = _rand_date(rng, date(2025, 1, 15), date(2025, 4, 15))
        v["acquired"] = min(v["acquired"], date(2024, 6, 30))
    used_plates = set()
    for v in vehicles:
        plate = f"{''.join(rng.choices('ABCDEFGHJKLMNPRSTUVWXYZ', k=3))}-{rng.randint(100, 999)}"
        while plate in used_plates:
            plate = f"{''.join(rng.choices('ABCDEFGHJKLMNPRSTUVWXYZ', k=3))}-{rng.randint(100, 999)}"
        used_plates.add(plate)
        v["plate_number"] = plate

    # ------------------------------------------------------------------ rentals
    rentals: List[dict] = []
    for v in vehicles:
        if v["never_rented"]:
            continue
        cursor = v["acquired"] + timedelta(days=rng.randint(1, 20))
        bound = v["retired_on"] or REF
        while cursor <= bound:
            duration = rng.choices(range(1, 15), weights=[8, 14, 16, 14, 12, 10, 8, 6, 4, 3, 2, 1, 1, 1])[0]
            start, end = cursor, cursor + timedelta(days=duration)
            year_factor = RATE_FACTOR[min(max(start.year, 2023), 2025)]
            rate = int(round(cat_rate[v["category_id"]] * year_factor, -2))
            roll = rng.random()
            status, actual, late_days = "completed", None, 0
            if roll < 0.07:
                status = "cancelled"
            elif end > REF:
                status = "active"
            else:
                late_days = rng.choices([0, 1, 2, 3], weights=[84, 8, 5, 3])[0]
                actual = end + timedelta(days=late_days)
                # a few rentals that ended in the last week are overdue and not returned yet
                if (REF - end).days <= 6 and rng.random() < 0.3:
                    status, actual, late_days = "active", None, 0
            pickup_branch = v["branch_id"] if rng.random() < 0.85 else rng.choice([b[0] for b in BRANCHES])
            return_branch = pickup_branch if rng.random() < 0.85 else rng.choice([b[0] for b in BRANCHES])
            total = 0
            if status != "cancelled":
                total = rate * duration + int(round(rate * LATE_FEE_RATE * late_days))
            if actual is not None and actual > REF:
                actual = REF
            rentals.append(
                {
                    "customer_id": rng.choices(range(1, n_customers + 1), weights=cust_weights)[0],
                    "vehicle_id": v["vehicle_id"],
                    "pickup_branch_id": pickup_branch,
                    "return_branch_id": return_branch if status != "cancelled" else pickup_branch,
                    "start_date": start,
                    "end_date": end,
                    "actual_return_date": actual,
                    "daily_rate": rate,
                    "total_amount": total,
                    "status": status,
                    "late_days": late_days,
                }
            )
            if status == "active" and end <= REF:
                break  # overdue vehicle: no later rentals can exist
            cursor = end + timedelta(days=rng.randint(2, 60))
    rentals.sort(key=lambda r: (r["start_date"], r["vehicle_id"]))
    for i, r in enumerate(rentals, start=1):
        r["rental_id"] = i

    # customers joined on or before their first rental; loyalty from completed rentals
    first_start: Dict[int, date] = {}
    completed_count: Dict[int, int] = {}
    for r in rentals:
        first_start[r["customer_id"]] = min(first_start.get(r["customer_id"], r["start_date"]), r["start_date"])
        if r["status"] == "completed":
            completed_count[r["customer_id"]] = completed_count.get(r["customer_id"], 0) + 1
    for c in customers:
        joined = date.fromisoformat(c["date_joined"])
        fs = first_start.get(c["customer_id"])
        if fs is not None and joined > fs:
            joined = fs - timedelta(days=rng.randint(0, 30))
        c["date_joined"] = _iso(joined)
        n = completed_count.get(c["customer_id"], 0)
        c["loyalty_tier"] = "Platinum" if n >= 14 else "Gold" if n >= 8 else "Silver" if n >= 3 else "Bronze"

    # ----------------------------------------------------------------- payments
    payments: List[Tuple] = []
    methods, method_w = ["card", "cash", "bank_transfer"], [50, 35, 15]

    def add_payment(rental_id: int, amount: int, when: date, status: str) -> None:
        if amount > 0:
            payments.append((rental_id, amount, _iso(when), rng.choices(methods, weights=method_w)[0], status))

    for r in rentals:
        rid, total = r["rental_id"], r["total_amount"]
        if r["status"] == "completed":
            recent = (REF - r["end_date"]).days <= 90
            actual = r["actual_return_date"]
            roll = rng.random()
            if recent and roll < 0.20:
                deposit = int(round(total * 0.3))
                add_payment(rid, deposit, r["start_date"], "paid")
                add_payment(rid, total - deposit, actual, "pending")
            elif roll < 0.75:
                add_payment(rid, total, r["start_date"], "paid")
            else:
                deposit = int(round(total * 0.3))
                add_payment(rid, deposit, r["start_date"], "paid")
                add_payment(rid, total - deposit, actual, "paid")
        elif r["status"] == "active":
            planned = r["daily_rate"] * max(1, (r["end_date"] - r["start_date"]).days)
            add_payment(rid, int(round(planned * 0.3)), r["start_date"], "paid")
        else:  # cancelled
            roll = rng.random()
            fee = int(round(r["daily_rate"] * 0.2 * max(1, (r["end_date"] - r["start_date"]).days)))
            if roll < 0.6:
                add_payment(rid, fee, r["start_date"], "refunded")
            elif roll < 0.7:
                add_payment(rid, fee, r["start_date"], "paid")

    # -------------------------------------------------------------- maintenance
    maintenance: List[Tuple] = []
    type_names = list(SERVICE_TYPES)
    type_weights = [SERVICE_TYPES[t][2] for t in type_names]
    active_vehicles = {r["vehicle_id"] for r in rentals if r["status"] == "active"}
    for v in vehicles:
        end_of_life = v["retired_on"] or REF
        days_owned = (end_of_life - v["acquired"]).days
        if v["never_rented"] or days_owned < 60 or rng.random() < 0.12:
            continue
        n = max(1, int(days_owned / rng.randint(120, 240)))
        for _ in range(n):
            stype = rng.choices(type_names, weights=type_weights)[0]
            lo, hi, _w = SERVICE_TYPES[stype]
            maintenance.append(
                (
                    v["vehicle_id"],
                    _iso(_rand_date(rng, v["acquired"] + timedelta(days=30), end_of_life)),
                    stype,
                    int(round(rng.randint(lo, hi), -2)),
                    f"{stype.replace('_', ' ').capitalize()} for {v['make']} {v['model']}",
                )
            )

    # vehicle status: rented / retired / maintenance / available
    candidates = [v for v in vehicles if v["vehicle_id"] not in active_vehicles and not v["retired_on"]
                  and not v["never_rented"]]
    in_workshop = {v["vehicle_id"] for v in rng.sample(candidates, 6)}
    for v in vehicles:
        if v["retired_on"]:
            v["status"] = "retired"
        elif v["vehicle_id"] in active_vehicles:
            v["status"] = "rented"
        elif v["vehicle_id"] in in_workshop:
            v["status"] = "maintenance"
            maintenance.append(
                (v["vehicle_id"], _iso(REF - timedelta(days=rng.randint(0, 3))), "repair",
                 int(round(rng.randint(30_000, 150_000), -2)), f"Repair in progress for {v['make']} {v['model']}")
            )
        else:
            v["status"] = "available"
        age_days = max(30, (REF - v["acquired"]).days)
        v["mileage"] = 0 if v["never_rented"] else int(rng.randint(2_000, 40_000) + age_days * rng.randint(40, 110))

    # -------------------------------------------------------------------- write
    conn = sqlite3.connect(str(path))
    try:
        conn.executescript(DDL)
        conn.executemany("INSERT INTO branches VALUES (?,?,?,?,?)", BRANCHES)
        conn.executemany("INSERT INTO vehicle_categories VALUES (?,?,?,?)", CATEGORIES)
        conn.executemany(
            "INSERT INTO customers VALUES (?,?,?,?,?,?,?,?,?,?)",
            [(c["customer_id"], c["first_name"], c["last_name"], c["email"], c["phone"], c["city"],
              c["license_number"], c["birth_date"], c["date_joined"], c["loyalty_tier"]) for c in customers],
        )
        conn.executemany(
            "INSERT INTO vehicles VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            [(v["vehicle_id"], v["plate_number"], v["make"], v["model"], v["year"], v["category_id"],
              v["branch_id"], _iso(v["acquired"]), v["mileage"], v["purchase_price"], v["status"])
             for v in sorted(vehicles, key=lambda x: x["vehicle_id"])],
        )
        conn.executemany(
            "INSERT INTO rentals VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            [(r["rental_id"], r["customer_id"], r["vehicle_id"], r["pickup_branch_id"], r["return_branch_id"],
              _iso(r["start_date"]), _iso(r["end_date"]),
              _iso(r["actual_return_date"]) if r["actual_return_date"] else None,
              r["daily_rate"], r["total_amount"], r["status"]) for r in rentals],
        )
        conn.executemany(
            "INSERT INTO payments (rental_id, amount, payment_date, method, status) VALUES (?,?,?,?,?)", payments
        )
        conn.executemany(
            "INSERT INTO maintenance (vehicle_id, service_date, service_type, cost, description) VALUES (?,?,?,?,?)",
            maintenance,
        )
        conn.commit()
        problems = conn.execute("PRAGMA foreign_key_check").fetchall()
        if problems:
            raise RuntimeError(f"Foreign key violations after seeding: {problems[:5]}")
        conn.execute("VACUUM")
    finally:
        conn.close()
    return path


def table_counts(path: Path | str = DB_PATH) -> Dict[str, int]:
    """Return {table: row_count} using a read-only connection."""
    conn = sqlite3.connect(f"{Path(path).resolve().as_uri()}?mode=ro", uri=True)
    try:
        return {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in TABLES}
    finally:
        conn.close()


def ensure_database(path: Path | str = DB_PATH) -> Path:
    """Build the database if it does not exist yet (used by the Streamlit app)."""
    path = Path(path)
    if not path.exists():
        build_database(path)
    return path


if __name__ == "__main__":
    out = build_database()
    print(f"Built {out}")
    for table, n in table_counts(out).items():
        print(f"  {table:<20}{n:>7}")
