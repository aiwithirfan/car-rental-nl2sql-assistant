"""DDL for the car rental database plus human-written column documentation.

The documentation is what the *full* schema prompt shows to the LLM. It is kept
separate from the DDL so the ablation study can switch it off cleanly.
"""
from __future__ import annotations

DDL = """
PRAGMA foreign_keys = ON;

CREATE TABLE branches (
    branch_id    INTEGER PRIMARY KEY,
    name         TEXT NOT NULL UNIQUE,
    city         TEXT NOT NULL,
    phone        TEXT NOT NULL,
    opened_date  TEXT NOT NULL
);

CREATE TABLE customers (
    customer_id     INTEGER PRIMARY KEY,
    first_name      TEXT NOT NULL,
    last_name       TEXT NOT NULL,
    email           TEXT NOT NULL UNIQUE,
    phone           TEXT NOT NULL,
    city            TEXT NOT NULL,
    license_number  TEXT NOT NULL UNIQUE,
    birth_date      TEXT NOT NULL,
    date_joined     TEXT NOT NULL,
    loyalty_tier    TEXT NOT NULL CHECK (loyalty_tier IN ('Bronze','Silver','Gold','Platinum'))
);

CREATE TABLE vehicle_categories (
    category_id  INTEGER PRIMARY KEY,
    name         TEXT NOT NULL UNIQUE,
    daily_rate   INTEGER NOT NULL,
    seats        INTEGER NOT NULL
);

CREATE TABLE vehicles (
    vehicle_id     INTEGER PRIMARY KEY,
    plate_number   TEXT NOT NULL UNIQUE,
    make           TEXT NOT NULL,
    model          TEXT NOT NULL,
    year           INTEGER NOT NULL,
    category_id    INTEGER NOT NULL REFERENCES vehicle_categories(category_id),
    branch_id      INTEGER NOT NULL REFERENCES branches(branch_id),
    acquired_date  TEXT NOT NULL,
    mileage        INTEGER NOT NULL,
    purchase_price INTEGER NOT NULL,
    status         TEXT NOT NULL CHECK (status IN ('available','rented','maintenance','retired'))
);

CREATE TABLE rentals (
    rental_id           INTEGER PRIMARY KEY,
    customer_id         INTEGER NOT NULL REFERENCES customers(customer_id),
    vehicle_id          INTEGER NOT NULL REFERENCES vehicles(vehicle_id),
    pickup_branch_id    INTEGER NOT NULL REFERENCES branches(branch_id),
    return_branch_id    INTEGER NOT NULL REFERENCES branches(branch_id),
    start_date          TEXT NOT NULL,
    end_date            TEXT NOT NULL,
    actual_return_date  TEXT,
    daily_rate          INTEGER NOT NULL,
    total_amount        INTEGER NOT NULL,
    status              TEXT NOT NULL CHECK (status IN ('completed','active','cancelled'))
);

CREATE TABLE payments (
    payment_id    INTEGER PRIMARY KEY,
    rental_id     INTEGER NOT NULL REFERENCES rentals(rental_id),
    amount        INTEGER NOT NULL,
    payment_date  TEXT NOT NULL,
    method        TEXT NOT NULL CHECK (method IN ('card','cash','bank_transfer')),
    status        TEXT NOT NULL CHECK (status IN ('paid','pending','refunded'))
);

CREATE TABLE maintenance (
    maintenance_id  INTEGER PRIMARY KEY,
    vehicle_id      INTEGER NOT NULL REFERENCES vehicles(vehicle_id),
    service_date    TEXT NOT NULL,
    service_type    TEXT NOT NULL,
    cost            INTEGER NOT NULL,
    description     TEXT NOT NULL
);

CREATE INDEX idx_vehicles_branch ON vehicles(branch_id);
CREATE INDEX idx_vehicles_category ON vehicles(category_id);
CREATE INDEX idx_rentals_customer ON rentals(customer_id);
CREATE INDEX idx_rentals_vehicle ON rentals(vehicle_id);
CREATE INDEX idx_rentals_start ON rentals(start_date);
CREATE INDEX idx_payments_rental ON payments(rental_id);
CREATE INDEX idx_maintenance_vehicle ON maintenance(vehicle_id);
"""

TABLE_DOCS = {
    "branches": "Physical rental branches (one per city).",
    "customers": "Registered customers who can rent vehicles.",
    "vehicle_categories": "Vehicle classes with the current list daily rate in PKR.",
    "vehicles": "Every vehicle the company owns, including retired ones.",
    "rentals": "One row per booking. Cancelled bookings are kept with total_amount = 0.",
    "payments": "Money movements for rentals (paid, pending or refunded).",
    "maintenance": "Service and repair history of vehicles.",
}

COLUMN_DOCS = {
    "branches": {
        "branch_id": "Primary key.",
        "name": "Branch name, e.g. 'Lahore Gulberg'.",
        "city": "City the branch is in.",
        "phone": "Branch phone number.",
        "opened_date": "Date the branch opened (YYYY-MM-DD).",
    },
    "customers": {
        "customer_id": "Primary key.",
        "first_name": "Customer first name.",
        "last_name": "Customer last name.",
        "email": "Unique e-mail address.",
        "phone": "Mobile phone number.",
        "city": "Home city of the customer.",
        "license_number": "Driving licence number.",
        "birth_date": "Date of birth (YYYY-MM-DD).",
        "date_joined": "Date the customer registered (YYYY-MM-DD).",
        "loyalty_tier": "One of Bronze, Silver, Gold, Platinum (capitalised).",
    },
    "vehicle_categories": {
        "category_id": "Primary key.",
        "name": "Category name: Economy, Compact, Sedan, SUV, Luxury or Van.",
        "daily_rate": "Current list price per day in PKR.",
        "seats": "Number of seats.",
    },
    "vehicles": {
        "vehicle_id": "Primary key.",
        "plate_number": "Unique number plate.",
        "make": "Manufacturer, e.g. Toyota, Honda, Suzuki.",
        "model": "Model name, e.g. Corolla.",
        "year": "Model year of the vehicle.",
        "category_id": "FK to vehicle_categories.category_id.",
        "branch_id": "FK to branches.branch_id (home branch).",
        "acquired_date": "Date the company bought the vehicle.",
        "mileage": "Odometer reading in km.",
        "purchase_price": "Purchase price in PKR.",
        "status": "Current state: available, rented, maintenance or retired (lowercase).",
    },
    "rentals": {
        "rental_id": "Primary key.",
        "customer_id": "FK to customers.customer_id.",
        "vehicle_id": "FK to vehicles.vehicle_id.",
        "pickup_branch_id": "FK to branches.branch_id where the vehicle was picked up.",
        "return_branch_id": "FK to branches.branch_id where it is returned (differs for one-way rentals).",
        "start_date": "First day of the rental (YYYY-MM-DD).",
        "end_date": "Planned last day of the rental (YYYY-MM-DD).",
        "actual_return_date": "Date the vehicle really came back; NULL if not returned (active or cancelled).",
        "daily_rate": "Rate charged per day in PKR (may differ from the category's current rate).",
        "total_amount": "Total price in PKR: daily_rate x rental days + late fee; 0 when cancelled.",
        "status": "completed, active or cancelled (lowercase).",
    },
    "payments": {
        "payment_id": "Primary key.",
        "rental_id": "FK to rentals.rental_id.",
        "amount": "Amount in PKR.",
        "payment_date": "Date paid (or due date when status is pending).",
        "method": "card, cash or bank_transfer.",
        "status": "paid, pending or refunded.",
    },
    "maintenance": {
        "maintenance_id": "Primary key.",
        "vehicle_id": "FK to vehicles.vehicle_id.",
        "service_date": "Date of the service (YYYY-MM-DD).",
        "service_type": "oil_change, inspection, brake_service, tire_replacement, repair or detailing.",
        "cost": "Cost in PKR.",
        "description": "Free-text note.",
    },
}

BUSINESS_NOTES = """\
Business rules and conventions:
- All dates are TEXT in ISO format YYYY-MM-DD; use SQLite date functions (strftime, julianday, date).
- Rental length in days = julianday(end_date) - julianday(start_date).
- A rental is "late" when actual_return_date > end_date (completed rentals only).
- An active rental is "overdue" when status = 'active' and end_date is before today's date.
- A one-way rental has return_branch_id <> pickup_branch_id.
- Revenue from rentals = SUM(rentals.total_amount); cash actually received = SUM(payments.amount) with status = 'paid'.
- Vehicle category names and branch names are both stored in a column called "name" - always qualify it.
- Money columns are whole PKR amounts (integers)."""
