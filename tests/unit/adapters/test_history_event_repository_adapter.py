from datetime import UTC, datetime

from sqlmodel import select

from app.adapters.history_event_repository_adapter import HistoryEventRepositoryAdapter
from app.models.application.index import Application
from app.models.history.enums import ActorType, EventReference
from app.models.history.index import HistoryEvent


def test_create_history_event_persists_event_with_expected_values(session):
    laa_reference = session.exec(select(Application)).first().laa_reference
    adapter = HistoryEventRepositoryAdapter(session)

    created = adapter.create_history_event(
        event_reference=EventReference.APPLICATION_SUBMITTED,
        actor="test_user@example.com",
        actor_type=ActorType.CASEWORKER,
        event_description="Application submitted",
        laa_reference=str(laa_reference),
        event_data="Additional context data",
    )

    stored = session.get(HistoryEvent, created.id)

    assert created.id is not None
    assert stored is not None
    assert stored.event_reference == EventReference.APPLICATION_SUBMITTED
    assert stored.actor == "test_user@example.com"
    assert stored.event_description == "Application submitted"
    assert stored.laa_reference == laa_reference
    assert stored.event_data == "Additional context data"


def test_create_history_event_sets_timestamp_automatically(session):
    laa_reference = session.exec(select(Application)).first().laa_reference
    adapter = HistoryEventRepositoryAdapter(session)

    before_creation = datetime.now(UTC)
    created = adapter.create_history_event(
        event_reference=EventReference.APPLICATION_SUBMITTED,
        actor="test_user@example.com",
        actor_type=ActorType.CASEWORKER,
        event_description="Test event",
        laa_reference=str(laa_reference),
    )
    after_creation = datetime.now(UTC)

    assert created.timestamp is not None
    # SQLite doesn't preserve timezone info, so we need to make it timezone-aware for comparison
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
        event_reference=EventReference.APPLICATION_SUBMITTED,
        actor="test_user@example.com",
        actor_type=ActorType.CASEWORKER,
        event_description="Event without data",
        laa_reference=str(laa_reference),
        event_data=None,
    )

    stored = session.get(HistoryEvent, created.id)

    assert stored is not None
    assert stored.event_data is None


def test_commits_transaction(session):
    laa_reference = session.exec(select(Application)).first().laa_reference
    adapter = HistoryEventRepositoryAdapter(session)

    created = adapter.create_history_event(
        event_reference=EventReference.APPLICATION_SUBMITTED,
        actor="test_user@example.com",
        actor_type=ActorType.CASEWORKER,
        event_description="Event to commit",
        laa_reference=str(laa_reference),
    )
    adapter.commit()

    # Verify event persists after commit
    stored = session.get(HistoryEvent, created.id)
    assert stored is not None
    assert stored.event_reference == EventReference.APPLICATION_SUBMITTED


def test_rollback_discards_uncommitted_event(session):
    laa_reference = session.exec(select(Application)).first().laa_reference
    adapter = HistoryEventRepositoryAdapter(session)

    created = adapter.create_history_event(
        event_reference=EventReference.APPLICATION_SUBMITTED,
        actor="test_user@example.com",
        actor_type=ActorType.CASEWORKER,
        event_description="Event to rollback",
        laa_reference=str(laa_reference),
    )
    event_id = created.id
    adapter.rollback()

    # Verify event does not persist after rollback
    stored = session.get(HistoryEvent, event_id)
    assert stored is None
