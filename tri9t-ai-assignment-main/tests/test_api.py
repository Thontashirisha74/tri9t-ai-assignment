
from fastapi.testclient import TestClient
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_unknown_generation_returns_404():
    response = client.get(
        "/generations/00000000-0000-0000-0000-000000000000"
    )

    assert response.status_code == 404


def test_generation_requires_selection_or_node():
    response = client.get("/generations")

    assert response.status_code == 422
