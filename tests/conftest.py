import pytest

from db import connect
from init_db import seed


@pytest.fixture
def db(tmp_path):
    """A fresh, seeded database per test - tests never touch data/venues.db."""
    path = tmp_path / "test.db"
    with connect(path) as conn:
        seed(conn)
    return path
