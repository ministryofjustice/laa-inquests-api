from datetime import UTC, datetime

from app.adapters import history_event_repository_adapter as history_adapter
from app.adapters.history_event_repository_adapter import HistoryEventRepositoryAdapter
from app.models.history.enums import ActorType, HistoryEventReference
from app.models.history.index import HistoryEvent
from tests.e2e.factories import create_application_in_db, create_claim_in_db

FROM = datetime(2025, 3, 1, tzinfo=UTC)
BEFORE = datetime(2025, 4, 1, tzinfo=UTC)
IN_RANGE = datetime(2025, 3, 15, 12, 0, tzinfo=UTC)
SUBMITTED_AT = datetime(2025, 3, 2, 9, 30, tzinfo=UTC)


def _add_event(
    session,
    application,
    reference=HistoryEventReference.APPLICATION_ASSESSMENT_COMPLETED,
    event_data=None,
    timestamp=IN_RANGE,
    actor="Jane Smith",
    actor_type=ActorType.CASEWORKER,
    actor_email_address="jane.smith@example.com",
):
    event = HistoryEvent(
        event_reference=reference,
        timestamp=timestamp,
        actor=actor,
        actor_type=actor_type,
        actor_email_address=actor_email_address,
        event_data={"merits_decision": "Granted"} if event_data is None else event_data,
        application_id=application.application_id,
    )
    session.add(event)
    session.commit()
    return event


def _application(session):
    return create_application_in_db(session, created_at=SUBMITTED_AT)


def _records(session):
    return HistoryEventRepositoryAdapter(session).get_decisions_report_records(
        FROM, BEFORE
    )


def test_returns_application_decision_with_application_details(session):
    application = _application(session)
    _add_event(session, application)

    [record] = _records(session)

    assert record.event_reference == (
        HistoryEventReference.APPLICATION_ASSESSMENT_COMPLETED
    )
    assert record.actor == "Jane Smith"
    assert record.event_data == {"merits_decision": "Granted"}
    assert record.laa_reference == application.laa_reference
    assert record.decided_at.replace(tzinfo=UTC) == IN_RANGE
    assert record.application_submitted_at.replace(tzinfo=UTC) == SUBMITTED_AT
    assert record.claim_submitted_at is None


def test_returns_actor_type_and_stored_email_address(session):
    _add_event(session, _application(session))

    [record] = _records(session)

    assert record.actor_type == ActorType.CASEWORKER
    assert record.actor_email_address == "jane.smith@example.com"


def test_historical_event_has_no_email_address(session):
    _add_event(session, _application(session), actor_email_address=None)

    [record] = _records(session)

    assert record.actor_email_address is None


def test_system_event_returns_system_actor_type_and_no_email(session):
    _add_event(
        session,
        _application(session),
        reference=HistoryEventReference.POA_AUTO_APPROVED,
        event_data={"claim_reference": "INQC-NOPE-NOPE"},
        actor="System",
        actor_type=ActorType.SYSTEM,
        actor_email_address=None,
    )

    [record] = _records(session)

    assert record.actor_type == ActorType.SYSTEM
    assert record.actor_email_address is None


def test_only_decision_events_are_returned(session):
    application = _application(session)
    for reference in (
        HistoryEventReference.APPLICATION_SUBMITTED,
        HistoryEventReference.CASE_NOTE_ADDED,
        HistoryEventReference.CLAIM_SUBMITTED,
        HistoryEventReference.APPLICATION_GRANTED_EMAIL,
    ):
        _add_event(session, application, reference, event_data={})
    for reference in (
        HistoryEventReference.APPLICATION_ASSESSMENT_COMPLETED,
        HistoryEventReference.CLAIM_ASSESSMENT_COMPLETED,
        HistoryEventReference.POA_AUTO_APPROVED,
        HistoryEventReference.POA_AUTO_REJECTED,
    ):
        _add_event(session, application, reference, event_data={})

    references = {record.event_reference for record in _records(session)}

    assert references == {
        HistoryEventReference.APPLICATION_ASSESSMENT_COMPLETED,
        HistoryEventReference.CLAIM_ASSESSMENT_COMPLETED,
        HistoryEventReference.POA_AUTO_APPROVED,
        HistoryEventReference.POA_AUTO_REJECTED,
    }


def test_range_is_inclusive_of_start_and_exclusive_of_end(session):
    application = _application(session)
    _add_event(
        session,
        application,
        timestamp=datetime(2025, 2, 28, 23, 59, 59, tzinfo=UTC),
        actor="before",
    )
    _add_event(session, application, timestamp=FROM, actor="start")
    _add_event(
        session,
        application,
        timestamp=datetime(2025, 3, 31, 23, 59, 59, tzinfo=UTC),
        actor="last",
    )
    _add_event(session, application, timestamp=BEFORE, actor="end")

    assert [record.actor for record in _records(session)] == ["start", "last"]


def test_records_are_ordered_by_timestamp_then_id(session):
    application = _application(session)
    _add_event(
        session,
        application,
        timestamp=datetime(2025, 3, 20, tzinfo=UTC),
        actor="latest",
    )
    _add_event(session, application, timestamp=IN_RANGE, actor="tie-first")
    _add_event(session, application, timestamp=IN_RANGE, actor="tie-second")
    _add_event(
        session,
        application,
        timestamp=datetime(2025, 3, 5, tzinfo=UTC),
        actor="earliest",
    )

    assert [record.actor for record in _records(session)] == [
        "earliest",
        "tie-first",
        "tie-second",
        "latest",
    ]


def test_claim_events_include_claim_submission_date(session):
    application = _application(session)
    claim_submitted_at = datetime(2025, 3, 4, 8, 0, tzinfo=UTC)
    claim = create_claim_in_db(
        session,
        application_id=application.application_id,
        submission_date=claim_submitted_at,
    )
    _add_event(
        session,
        application,
        HistoryEventReference.POA_AUTO_APPROVED,
        {"claim_reference": claim.claim_reference},
    )

    [record] = _records(session)

    assert record.claim_submitted_at.replace(tzinfo=UTC) == claim_submitted_at


def test_claim_event_for_unknown_claim_has_no_claim_submission_date(session):
    application = _application(session)
    _add_event(
        session,
        application,
        HistoryEventReference.POA_AUTO_APPROVED,
        {"claim_reference": "INQC-NOPE-NOPE"},
    )

    [record] = _records(session)

    assert record.claim_submitted_at is None


def test_claim_event_without_event_data_is_returned_for_domain_to_reject(session):
    application = _application(session)
    event = _add_event(session, application, HistoryEventReference.POA_AUTO_APPROVED)
    event.event_data = None
    session.add(event)
    session.commit()

    [record] = _records(session)

    assert record.event_data is None
    assert record.claim_submitted_at is None


def test_more_claims_than_one_lookup_batch_are_resolved(session, monkeypatch):
    monkeypatch.setattr(history_adapter, "CLAIM_LOOKUP_BATCH_SIZE", 2)
    application = _application(session)
    claims = [
        create_claim_in_db(session, application_id=application.application_id)
        for _ in range(3)
    ]
    for claim in claims:
        _add_event(
            session,
            application,
            HistoryEventReference.POA_AUTO_REJECTED,
            {"claim_reference": claim.claim_reference},
        )

    records = _records(session)

    assert len(records) == 3
    assert all(record.claim_submitted_at is not None for record in records)
