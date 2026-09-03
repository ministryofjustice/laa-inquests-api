from datetime import UTC, datetime

import pytest
from sqlmodel import select

from app.adapters.history_event_repository_adapter import HistoryEventRepositoryAdapter
from app.contexts.user import clear_entra_user_context, set_entra_user_context
from app.models.application.index import (
    Application,
    ApplicationProceeding,
    ApplicationPublicBody,
)
from app.models.history.enums import ActorType, HistoryEventReference
from app.models.history.index import HistoryEvent


def test_create_history_event_persists_event_with_expected_values(session):
    laa_reference = session.exec(select(Application)).first().laa_reference
    adapter = HistoryEventRepositoryAdapter(session)

    created = adapter.create_history_event(
        event_reference=HistoryEventReference.APPLICATION_SUBMITTED,
        actor="test_user@example.com",
        actor_type=ActorType.CASEWORKER,
        application_id=laa_reference,
        event_data={"context": "Additional context data", "related_link": None},
    )

    stored = session.get(HistoryEvent, created.id)

    assert created.id is not None
    assert stored is not None
    assert stored.event_reference == HistoryEventReference.APPLICATION_SUBMITTED
    assert stored.actor == "test_user@example.com"
    assert stored.laa_reference == laa_reference
    assert stored.event_data == {
        "context": "Additional context data",
        "related_link": None,
    }


def test_create_history_event_sets_timestamp_automatically(session):
    laa_reference = session.exec(select(Application)).first().laa_reference
    adapter = HistoryEventRepositoryAdapter(session)

    before_creation = datetime.now(UTC)
    created = adapter.create_history_event(
        event_reference=HistoryEventReference.APPLICATION_SUBMITTED,
        actor="test_user@example.com",
        actor_type=ActorType.CASEWORKER,
        application_id=laa_reference,
    )
    after_creation = datetime.now(UTC)

    assert created.timestamp is not None
    timestamp = (
        created.timestamp.replace(tzinfo=UTC)
        if created.timestamp.tzinfo is None
        else created.timestamp
    )
    assert before_creation <= timestamp <= after_creation


def test_create_history_event_handles_none_event_data(session):
    laa_reference = session.exec(select(Application)).first().laa_reference
    adapter = HistoryEventRepositoryAdapter(session)

    created = adapter.create_history_event(
        event_reference=HistoryEventReference.APPLICATION_SUBMITTED,
        actor="test_user@example.com",
        actor_type=ActorType.CASEWORKER,
        application_id=laa_reference,
        event_data=None,
    )

    stored = session.get(HistoryEvent, created.id)

    assert stored is not None
    assert stored.event_data is None


def test_create_history_raises_exception_for_missing_event_reference(session):
    laa_reference = session.exec(select(Application)).first().laa_reference
    adapter = HistoryEventRepositoryAdapter(session)

    with pytest.raises(ValueError):
        adapter.create_history_event(
            event_reference=None,
            actor="test_user@example.com",
            actor_type=ActorType.PROVIDER,
            application_id=laa_reference,
        )


def test_create_history_raises_exception_for_missing_actor(session):
    laa_reference = session.exec(select(Application)).first().laa_reference
    adapter = HistoryEventRepositoryAdapter(session)

    with pytest.raises(ValueError):
        adapter.create_history_event(
            event_reference=HistoryEventReference.APPLICATION_SUBMITTED,
            actor=None,
            actor_type=ActorType.PROVIDER,
            application_id=laa_reference,
        )


def test_create_history_raises_exception_for_empty_actor(session):
    laa_reference = session.exec(select(Application)).first().laa_reference
    adapter = HistoryEventRepositoryAdapter(session)

    with pytest.raises(ValueError):
        adapter.create_history_event(
            event_reference=HistoryEventReference.APPLICATION_SUBMITTED,
            actor="",
            actor_type=ActorType.PROVIDER,
            application_id=laa_reference,
        )


def test_create_history_raises_exception_for_missing_actor_type(session):
    laa_reference = session.exec(select(Application)).first().laa_reference
    adapter = HistoryEventRepositoryAdapter(session)

    with pytest.raises(ValueError):
        adapter.create_history_event(
            event_reference=HistoryEventReference.APPLICATION_SUBMITTED,
            actor="test_user@example.com",
            actor_type=None,
            application_id=laa_reference,
        )


def test_create_history_raises_exception_for_missing_laa_reference(session):
    adapter = HistoryEventRepositoryAdapter(session)

    with pytest.raises(ValueError):
        adapter.create_history_event(
            event_reference=HistoryEventReference.APPLICATION_SUBMITTED,
            actor="test_user@example.com",
            actor_type=ActorType.PROVIDER,
            application_id=None,
        )


def test_commits_transaction(session):
    laa_reference = session.exec(select(Application)).first().laa_reference
    adapter = HistoryEventRepositoryAdapter(session)

    created = adapter.create_history_event(
        event_reference=HistoryEventReference.APPLICATION_SUBMITTED,
        actor="test_user@example.com",
        actor_type=ActorType.CASEWORKER,
        application_id=laa_reference,
    )
    adapter.commit()

    stored = session.get(HistoryEvent, created.id)
    assert stored is not None
    assert stored.event_reference == HistoryEventReference.APPLICATION_SUBMITTED


def test_rollback_discards_uncommitted_event(session):
    laa_reference = session.exec(select(Application)).first().laa_reference
    adapter = HistoryEventRepositoryAdapter(session)

    created = adapter.create_history_event(
        event_reference=HistoryEventReference.APPLICATION_SUBMITTED,
        actor="test_user@example.com",
        actor_type=ActorType.CASEWORKER,
        application_id=laa_reference,
    )
    event_id = created.id
    adapter.rollback()

    stored = session.get(HistoryEvent, event_id)
    assert stored is None


def test_get_application_history_returns_correct_events(session):
    laa_reference = session.exec(select(Application)).first().laa_reference
    adapter = HistoryEventRepositoryAdapter(session)

    event1 = adapter.create_history_event(
        event_reference=HistoryEventReference.APPLICATION_SUBMITTED,
        actor="test_user@example.com",
        actor_type=ActorType.CASEWORKER,
        application_id=laa_reference,
    )

    event2 = adapter.create_history_event(
        event_reference=HistoryEventReference.APPLICATION_SUBMITTED,
        actor="test_user@example.com",
        actor_type=ActorType.CASEWORKER,
        application_id=laa_reference,
    )

    history = adapter.get_application_history(laa_reference)
    assert event1 in history
    assert event2 in history


def test_get_application_history_does_not_return_events_for_other_applications(session):
    application1 = session.exec(select(Application)).first()
    laa_reference1 = application1.laa_reference

    application2 = Application(
        proceeding=ApplicationProceeding(
            proceeding_id=application1.proceeding.proceeding_id,
        ),
        client_id=application1.client_id,
        deceased_id=application1.deceased.deceased_id,
        public_bodies=[
            ApplicationPublicBody(
                public_body_id=application1.public_bodies[0].public_body_id,
            )
        ],
        provider_id=application1.provider_id,
        new_laa_reference="INQ-YYY-YYY",
    )
    session.add(application2)
    session.flush()
    laa_reference2 = application2.laa_reference

    adapter = HistoryEventRepositoryAdapter(session)

    event1 = adapter.create_history_event(
        event_reference=HistoryEventReference.APPLICATION_SUBMITTED,
        actor="test_user@example.com",
        actor_type=ActorType.CASEWORKER,
        application_id=laa_reference1,
    )

    event2 = adapter.create_history_event(
        event_reference=HistoryEventReference.APPLICATION_SUBMITTED,
        actor="test_user@example.com",
        actor_type=ActorType.CASEWORKER,
        application_id=laa_reference2,
    )

    history1 = adapter.get_application_history(laa_reference1)
    history2 = adapter.get_application_history(laa_reference2)
    assert history1 == [event1]
    assert history2 == [event2]


def test_get_application_history_returns_event_list_in_reverse_chronological_order(
    session,
):
    laa_reference = session.exec(select(Application)).first().laa_reference
    adapter = HistoryEventRepositoryAdapter(session)

    event1 = adapter.create_history_event(
        event_reference=HistoryEventReference.APPLICATION_SUBMITTED,
        actor="test_user@example.com",
        actor_type=ActorType.CASEWORKER,
        application_id=laa_reference,
    )

    event2 = adapter.create_history_event(
        event_reference=HistoryEventReference.APPLICATION_SUBMITTED,
        actor="test_user@example.com",
        actor_type=ActorType.CASEWORKER,
        application_id=laa_reference,
    )

    history = adapter.get_application_history(laa_reference)
    assert history == [event2, event1]


def test_create_history_event_does_not_store_entra_object_id_for_system_actor(session):
    laa_reference = session.exec(select(Application)).first().laa_reference
    adapter = HistoryEventRepositoryAdapter(session)

    set_entra_user_context("entra-object-id-123", "Caseworker")
    try:
        created = adapter.create_history_event(
            event_reference=HistoryEventReference.APPLICATION_SUBMISSION_CONFIRMATION,
            actor=ActorType.SYSTEM,
            actor_type=ActorType.SYSTEM,
            application_id=laa_reference,
        )
    finally:
        clear_entra_user_context()

    stored = session.get(HistoryEvent, created.id)
    assert stored is not None
    assert stored.entra_user_object_id is None


def test_create_history_event_stores_entra_object_id_for_non_system_actor(session):
    laa_reference = session.exec(select(Application)).first().laa_reference
    adapter = HistoryEventRepositoryAdapter(session)

    set_entra_user_context("entra-object-id-123", "Caseworker")
    try:
        created = adapter.create_history_event(
            event_reference=HistoryEventReference.APPLICATION_ASSESSMENT_COMPLETED,
            actor="caseworker@example.com",
            actor_type=ActorType.CASEWORKER,
            application_id=laa_reference,
        )
    finally:
        clear_entra_user_context()

    stored = session.get(HistoryEvent, created.id)
    assert stored is not None
    assert stored.entra_user_object_id == "entra-object-id-123"
