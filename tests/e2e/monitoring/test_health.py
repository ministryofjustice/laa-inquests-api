from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError
from sqlmodel import Session


def test_200_health_response_contains_expected_body(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == "Healthy"


def test_200_health_does_not_query_unavailable_database(
    client: TestClient, session: Session
) -> None:
    with patch.object(
        session,
        "execute",
        side_effect=OperationalError(
            "SELECT 1", {}, Exception("Database connection refused")
        ),
    ) as execute:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == "Healthy"
    execute.assert_not_called()
