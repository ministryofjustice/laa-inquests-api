from datetime import UTC, datetime

from sqlmodel import select

from app.models.application.index import Application
from app.models.history.enums import ActorType, HistoryEventReference
from app.models.history.index import HistoryEvent


def test_401_get_application_history_returns_401_when_no_authorization_header(
    entra_auth_client, session
):
    first_application_row = session.exec(select(Application)).first()
    laa_reference = first_application_row.__dict__["application_id"]

    response = entra_auth_client.get(f"/applications/{laa_reference}/history")

    assert response.status_code == 401


def test_403_get_application_history_returns_403_when_provider_token(
    entra_auth_client, session
):
    first_application_row = session.exec(select(Application)).first()
    laa_reference = first_application_row.__dict__["application_id"]

    response = entra_auth_client.get(
        f"/applications/{laa_reference}/history",
        headers={"Authorization": "Bearer valid-provider-entra-token"},
    )

    assert response.status_code == 403


def test_200_get_application_history_returns_events_for_application_that_exists(
    entra_auth_client, session
):
    first_application_row = session.exec(select(Application)).first()
    laa_reference = first_application_row.__dict__["application_id"]

    # Create a history event for the application
    history_event = HistoryEvent(
        event_reference=HistoryEventReference.APPLICATION_SUBMITTED,
        timestamp=datetime.now(UTC),
        actor="provider@example.com",
        actor_type=ActorType.PROVIDER,
        event_data=None,
        application_id=laa_reference,
    )
    session.add(history_event)
    session.commit()

    response = entra_auth_client.get(
        f"/applications/{laa_reference}/history",
        headers={"Authorization": "Bearer valid-caseworker-entra-token"},
    )

    assert response.status_code == 200
    events = response.json()
    assert len(events) == 1
    assert events[0]["eventReference"] == HistoryEventReference.APPLICATION_SUBMITTED
    assert events[0]["actor"] == "Provider"


def test_404_get_application_history_returns_404_for_application_that_does_not_exist(
    entra_auth_client,
):
    non_existent_laa_reference = 999999

    response = entra_auth_client.get(
        f"/applications/{non_existent_laa_reference}/history",
        headers={"Authorization": "Bearer valid-caseworker-entra-token"},
    )

    assert response.status_code == 404


def test_200_get_application_history_returns_empty_list_when_no_events_exist(
    entra_auth_client, session
):
    first_application_row = session.exec(select(Application)).first()
    laa_reference = first_application_row.__dict__["application_id"]

    response = entra_auth_client.get(
        f"/applications/{laa_reference}/history",
        headers={"Authorization": "Bearer valid-caseworker-entra-token"},
    )

    assert response.status_code == 200
    events = response.json()
    assert events == []


def test_200_get_application_history_returns_events_in_reverse_chronological_order(
    entra_auth_client, session
):
    first_application_row = session.exec(select(Application)).first()
    laa_reference = first_application_row.__dict__["application_id"]

    event1 = HistoryEvent(
        event_reference=HistoryEventReference.APPLICATION_SUBMITTED,
        timestamp=datetime.now(UTC),
        actor="provider@example.com",
        actor_type=ActorType.PROVIDER,
        event_data=None,
        application_id=laa_reference,
    )
    session.add(event1)
    session.commit()

    event2 = HistoryEvent(
        event_reference=HistoryEventReference.APPLICATION_ASSESSMENT_COMPLETED,
        timestamp=datetime.now(UTC),
        actor="caseworker@example.com",
        actor_type=ActorType.CASEWORKER,
        event_data={"decision": "granted", "related_link": "/certificate/123"},
        application_id=laa_reference,
    )
    session.add(event2)
    session.commit()

    event3 = HistoryEvent(
        event_reference=HistoryEventReference.CERTIFICATE_CREATED,
        timestamp=datetime.now(UTC),
        actor="System",
        actor_type=ActorType.SYSTEM,
        event_data=None,
        application_id=laa_reference,
    )
    session.add(event3)
    session.commit()

    response = entra_auth_client.get(
        f"/applications/{laa_reference}/history",
        headers={"Authorization": "Bearer valid-caseworker-entra-token"},
    )

    assert response.status_code == 200
    events = response.json()
    assert len(events) == 3
    assert events[0]["eventReference"] == HistoryEventReference.CERTIFICATE_CREATED
    assert (
        events[1]["eventReference"]
        == HistoryEventReference.APPLICATION_ASSESSMENT_COMPLETED
    )
    assert events[1]["eventData"]["relatedLink"] == "/certificate/123"
    assert "related_link" not in events[1]["eventData"]
    assert events[2]["eventReference"] == HistoryEventReference.APPLICATION_SUBMITTED
    assert events[0]["timestamp"] > events[1]["timestamp"] > events[2]["timestamp"]
