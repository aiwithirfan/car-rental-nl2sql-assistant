import pytest

from car_rental_sql.database import build_database


@pytest.fixture(scope="session")
def db_path(tmp_path_factory):
    """A freshly built database so tests never depend on the committed file."""
    return build_database(tmp_path_factory.mktemp("db") / "test.db")
