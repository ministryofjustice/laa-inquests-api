from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError, SQLAlchemyError, TimeoutError
from sqlmodel import Session

from app.routers.monitoring import get_readiness_session_factory


def test_200_status_checks_database_and_contains_expected_body(
    client: TestClient, session: Session
) -> None:
    with patch.object(session, "execute", wraps=session.execute) as execute:
        response = client.get("/status")

    assert response.status_code == 200
    assert response.json() == "OK"
    execute.assert_called()


@pytest.mark.parametrize(
    "database_error",
    [
        OperationalError(
            "SELECT 1", {}, Exception("Database connection refused: private details")
        ),
        TimeoutError("Database connection timed out: private details"),
    ],
    ids=["connection-failure", "timeout"],
)
def test_503_status_returns_generic_error_when_database_check_fails(
    client: TestClient, session: Session, database_error: SQLAlchemyError
) -> None:
    with patch.object(session, "execute", side_effect=database_error):
        response = client.get("/status")

    assert response.status_code == 503
    assert response.json() == {"detail": "Service unavailable"}


def test_503_status_returns_generic_error_when_database_session_cannot_be_created(
    client: TestClient,
) -> None:
    def unavailable_session() -> None:
        raise OperationalError(
            "SELECT 1", {}, Exception("Database connection refused: private details")
        )

    previous_override = client.app.dependency_overrides[get_readiness_session_factory]
    client.app.dependency_overrides[get_readiness_session_factory] = (
        lambda: unavailable_session
    )
    try:
        response = client.get("/status")
    finally:
        client.app.dependency_overrides[get_readiness_session_factory] = (
            previous_override
        )

    assert response.status_code == 503
    assert response.json() == {"detail": "Service unavailable"}


def test_200_status_recovers_after_database_becomes_available(
    client: TestClient, session: Session
) -> None:
    with patch.object(
        session,
        "execute",
        side_effect=OperationalError(
            "SELECT 1", {}, Exception("Database connection refused")
        ),
    ):
        unavailable_response = client.get("/status")

    recovered_response = client.get("/status")

    assert unavailable_response.status_code == 503
    assert recovered_response.status_code == 200
    assert recovered_response.json() == "OK"
