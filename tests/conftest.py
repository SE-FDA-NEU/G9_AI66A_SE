import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
import pytest
import sys
sys.path.insert(0, 'G9_AI66A_SE/src')
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
def client(db, tmp_path):
    app = create_app(database=db)
    app.config["UPLOAD_DIR"] = tmp_path / "uploads"
    return app.test_client()


@pytest.fixture
def login(client):
    """login("minh@example.com") signs in through the real /login form.
    Every seeded account has the password sanbong1."""
    def sign_in(email, password=None):
        return client.post("/login", data={"email": email, "password": password or "sanbong1"})
    return sign_in
