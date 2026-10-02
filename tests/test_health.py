"""The app starts and answers - the smallest test CI can run."""
from app import create_app


def test_health_reports_seeded_venues(db):
    client = create_app(database=db).test_client()
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok", "venues": 24}
