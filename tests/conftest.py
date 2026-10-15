import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
import pytest

from app import create_app
from db import connect
from init_db import seed

@pytest.fixture
def db(tmp_path):
    """A fresh, seeded database per test - tests never touch data/venues.db."""
    path = tmp_path / "test.db"
    with connect(path) as conn:
        seed(conn)
    return path


@pytest.fixture
def client(db):
    return create_app(database=db).test_client()


TEST_PASS = "sanbong1"


@pytest.fixture
def login(client):
    """login("minh@example.com") signs in through the real /login form.
    Every seeded account has the password sanbong1."""
    def sign_in(email, password=TEST_PASS):
        return client.post("/login", data={"email": email, "password": password})
    return sign_in
