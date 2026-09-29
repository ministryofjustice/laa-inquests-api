from datetime import UTC, datetime

from app.auth.rbac import Role
from app.models.history.enums import ActorType, HistoryEventReference
from tests.factories.persisted import create_history_event


def test_200_get_application_history_returns_events_for_application_that_exists(
    client, session, seeded_application
):
    laa_reference = seeded_application.laa_reference

    create_history_event(
        session,
        seeded_application,
        event_reference=HistoryEventReference.APPLICATION_SUBMITTED,
        actor="provider@example.com",
    )

    response = client.get(
        f"/applications/{laa_reference}/history",
        headers={"Authorization": f"Bearer {Role.APPLICATIONS_CASEWORKER.value}"},
    )

    assert response.status_code == 200
    events = response.json()
    assert len(events) == 1
    assert events[0]["eventReference"] == HistoryEventReference.APPLICATION_SUBMITTED
    assert events[0]["actor"] == "Provider"


def test_404_get_application_history_returns_404_for_application_that_does_not_exist(
    client,
):
    non_existent_laa_reference = 999999

    response = client.get(
        f"/applications/{non_existent_laa_reference}/history",
        headers={"Authorization": f"Bearer {Role.APPLICATIONS_CASEWORKER.value}"},
    )

    assert response.status_code == 404


def test_200_get_application_history_returns_empty_list_when_no_events_exist(
    client, seeded_application
):
    laa_reference = seeded_application.laa_reference

    response = client.get(
        f"/applications/{laa_reference}/history",
        headers={"Authorization": f"Bearer {Role.APPLICATIONS_CASEWORKER.value}"},
    )

    assert response.status_code == 200
    events = response.json()
    assert events == []


def test_200_get_application_history_returns_events_in_reverse_chronological_order(
    client, session, seeded_application
):
    laa_reference = seeded_application.laa_reference

    create_history_event(
        session,
        seeded_application,
        event_reference=HistoryEventReference.APPLICATION_SUBMITTED,
        timestamp=datetime.now(UTC),
        actor="provider@example.com",
    )
    create_history_event(
        session,
        seeded_application,
        event_reference=HistoryEventReference.APPLICATION_ASSESSMENT_COMPLETED,
        timestamp=datetime.now(UTC),
        actor="caseworker@example.com",
        actor_type=ActorType.CASEWORKER,
        event_data={"decision": "granted", "related_link": "/certificate/123"},
    )
    create_history_event(
        session,
        seeded_application,
        event_reference=HistoryEventReference.CERTIFICATE_CREATED,
        timestamp=datetime.now(UTC),
        actor="System",
        actor_type=ActorType.SYSTEM,
    )

    response = client.get(
        f"/applications/{laa_reference}/history",
        headers={"Authorization": f"Bearer {Role.APPLICATIONS_CASEWORKER.value}"},
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
