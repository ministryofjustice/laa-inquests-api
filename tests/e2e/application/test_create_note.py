from unittest.mock import patch

import pytest
from sqlmodel import select

from app.adapters.history_event_repository_adapter import HistoryEventRepositoryAdapter
from app.models.application.index import Application
from app.models.history.enums import ActorType
from app.models.history.index import HistoryEvent


@pytest.fixture
def application(session) -> Application:
    return session.exec(select(Application)).first()


def _caseworker_headers(auth_token: str) -> dict[str, str]:
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {auth_token}",
    }


def test_204_create_note_adds_caseworker_history_event(
    session, client, auth_token, application
):
    note_text = "Case note with useful information."

    response = client.post(
        f"/applications/{application.laa_reference}/history/note",
        json={"noteText": note_text},
        headers=_caseworker_headers(auth_token),
    )

    assert response.status_code == 204
    assert response.content == b""

    history_events = session.exec(
        select(HistoryEvent).where(
            HistoryEvent.laa_reference == application.laa_reference
        )
    ).all()
    history_event = next(
        event
        for event in history_events
        if event.event_reference.value == "EVT-BUS-X-001"
    )
    assert history_event.actor == "Test Name"
    assert history_event.actor_type == ActorType.CASEWORKER
    assert history_event.event_data == {"note_text": note_text}


def test_204_create_note_accepts_10_000_characters(
    session, client, auth_token, application
):
    note_text = "a" * 10_000

    response = client.post(
        f"/applications/{application.laa_reference}/history/note",
        json={"noteText": note_text},
        headers=_caseworker_headers(auth_token),
    )

    assert response.status_code == 204
    history_events = session.exec(
        select(HistoryEvent).where(
            HistoryEvent.laa_reference == application.laa_reference
        )
    ).all()
    assert any(event.event_data == {"note_text": note_text} for event in history_events)


@pytest.mark.parametrize(
    "request_body",
    [
        {},
        {"noteText": ""},
        {"noteText": " \t\n"},
        {"noteText": "a" * 10_001},
    ],
)
def test_422_create_note_rejects_invalid_note_text(
    client, auth_token, application, request_body
):
    response = client.post(
        f"/applications/{application.laa_reference}/history/note",
        json=request_body,
        headers=_caseworker_headers(auth_token),
    )

    assert response.status_code == 422


def test_404_create_note_returns_not_found_for_missing_application(client, auth_token):
    response = client.post(
        "/applications/99999/history/note",
        json={"noteText": "Case note"},
        headers=_caseworker_headers(auth_token),
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Application not found"}


def test_401_create_note_requires_authorization(entra_auth_client, application):
    response = entra_auth_client.post(
        f"/applications/{application.laa_reference}/history/note",
        json={"noteText": "Case note"},
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 401


def test_403_create_note_rejects_provider_token(entra_auth_client, application):
    response = entra_auth_client.post(
        f"/applications/{application.laa_reference}/history/note",
        json={"noteText": "Case note"},
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer valid-provider-entra-token",
        },
    )

    assert response.status_code == 403


def test_500_create_note_returns_generic_error_when_history_event_cannot_be_saved(
    session, client, auth_token, application
):
    with patch.object(
        HistoryEventRepositoryAdapter,
        "create_history_event",
        side_effect=Exception("History event persistence failed"),
    ):
        response = client.post(
            f"/applications/{application.laa_reference}/history/note",
            json={"noteText": "Case note"},
            headers=_caseworker_headers(auth_token),
        )

    assert response.status_code == 500
    assert response.json() == {"detail": "An internal server error occurred"}
    assert (
        session.exec(
            select(HistoryEvent).where(
                HistoryEvent.laa_reference == application.laa_reference
            )
        ).all()
        == []
    )
