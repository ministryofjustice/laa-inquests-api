from datetime import UTC, datetime

from sqlmodel import select

from app.adapters.audit_trail_repository_adapter import AuditTrailRepositoryAdapter
from app.domain.audit_trail import AuditTrailEvent
from app.models.application.index import Application
from app.models.audit.enums import ApplicationPageType, ReportType
from app.models.audit.index import ReportAudit, ViewApplicationPagesAudit
from app.models.history.enums import ActorType, HistoryEventReference
from app.models.history.index import HistoryEvent

FROM = datetime(2025, 3, 1, tzinfo=UTC)
BEFORE = datetime(2025, 4, 1, tzinfo=UTC)
IN_RANGE = datetime(2025, 3, 15, 12, 0, tzinfo=UTC)


def _history_event(session, **overrides) -> HistoryEvent:
    application = session.exec(select(Application)).first()
    values = {
        "event_reference": HistoryEventReference.APPLICATION_SUBMITTED,
        "timestamp": IN_RANGE,
        "actor": "provider@example.com",
        "actor_type": ActorType.PROVIDER,
        "application_id": application.application_id,
    }
    event = HistoryEvent(**(values | overrides))
    session.add(event)
    session.commit()
    return event


def _view_event(session, **overrides) -> ViewApplicationPagesAudit:
    values = {
        "timestamp": IN_RANGE,
        "user_email_address": "caseworker@example.com",
        "laa_reference": "INQ-123-456",
        "page": ApplicationPageType.OVERVIEW,
    }
    event = ViewApplicationPagesAudit(**(values | overrides))
    session.add(event)
    session.commit()
    return event


def _report_event(session, **overrides) -> ReportAudit:
    values = {
        "timestamp": IN_RANGE,
        "user_email_address": "assurance@example.com",
        "report_type": ReportType.CLAIMS_BACKLOG,
    }
    event = ReportAudit(**(values | overrides))
    session.add(event)
    session.commit()
    return event


def test_history_events_include_the_case_reference_and_provider_firm_details(session):
    _history_event(session, event_data={"key": "value"})

    events = list(
        AuditTrailRepositoryAdapter(session).iter_history_events(FROM, BEFORE)
    )

    assert events == [
        AuditTrailEvent(
            occurred_at=IN_RANGE,
            event_reference="EVT-BUS-APP-001",
            username="provider@example.com",
            laa_reference="INQ-123-456",
            firm_code="0A123B",
            office_id="0U651L",
            event_data={"key": "value"},
        )
    ]


def test_history_events_report_the_caseworker_email_and_no_firm_details(session):
    _history_event(
        session,
        event_reference=HistoryEventReference.APPLICATION_ASSESSMENT_COMPLETED,
        actor="Test Name",
        actor_type=ActorType.CASEWORKER,
        actor_email_address="caseworker@example.com",
    )

    (event,) = AuditTrailRepositoryAdapter(session).iter_history_events(FROM, BEFORE)

    assert event.event_reference == "EVT-BUS-APP-002"
    assert event.username == "caseworker@example.com"
    assert event.firm_code is None
    assert event.office_id is None


def test_history_events_filter_on_a_half_open_utc_range_and_sort_by_time_then_id(
    session,
):
    outside = [
        datetime(2025, 2, 28, 23, 59, 59, tzinfo=UTC),
        datetime(2025, 4, 1, 0, 0, 0, tzinfo=UTC),
    ]
    for timestamp in outside:
        _history_event(
            session, actor=f"outside-{timestamp:%d}@example.com", timestamp=timestamp
        )
    _history_event(
        session,
        actor="end@example.com",
        timestamp=datetime(2025, 3, 31, 23, 59, 59, tzinfo=UTC),
    )
    _history_event(session, actor="tie-1@example.com", timestamp=IN_RANGE)
    _history_event(session, actor="tie-2@example.com", timestamp=IN_RANGE)
    _history_event(session, actor="start@example.com", timestamp=FROM)

    events = AuditTrailRepositoryAdapter(session).iter_history_events(FROM, BEFORE)

    assert [event.username for event in events] == [
        "start@example.com",
        "tie-1@example.com",
        "tie-2@example.com",
        "end@example.com",
    ]


def test_application_view_events_map_each_page_and_report_the_viewer(session):
    _view_event(session, page=ApplicationPageType.OVERVIEW, timestamp=IN_RANGE)
    _view_event(
        session,
        page=ApplicationPageType.CERTIFICATE,
        timestamp=datetime(2025, 3, 15, 13, 0, tzinfo=UTC),
    )

    events = list(
        AuditTrailRepositoryAdapter(session).iter_application_view_events(FROM, BEFORE)
    )

    assert events == [
        AuditTrailEvent(
            occurred_at=IN_RANGE,
            event_reference="EVT-AUD-001",
            username="caseworker@example.com",
            laa_reference="INQ-123-456",
        ),
        AuditTrailEvent(
            occurred_at=datetime(2025, 3, 15, 13, 0, tzinfo=UTC),
            event_reference="EVT-AUD-003",
            username="caseworker@example.com",
            laa_reference="INQ-123-456",
        ),
    ]


def test_application_view_events_filter_on_a_half_open_utc_range(session):
    for hour_offset, user in enumerate(["before", "start", "end", "after"]):
        timestamp = [
            datetime(2025, 2, 28, 23, 59, 59, tzinfo=UTC),
            FROM,
            datetime(2025, 3, 31, 23, 59, 59, tzinfo=UTC),
            BEFORE,
        ][hour_offset]
        _view_event(
            session, user_email_address=f"{user}@example.com", timestamp=timestamp
        )

    events = AuditTrailRepositoryAdapter(session).iter_application_view_events(
        FROM, BEFORE
    )

    assert [event.username for event in events] == [
        "start@example.com",
        "end@example.com",
    ]


def test_report_events_carry_the_report_name_and_filter_on_a_half_open_range(session):
    _report_event(session, report_type=ReportType.PAYMENT_EXTRACT, timestamp=FROM)
    _report_event(session, report_type=ReportType.AUDIT_TRAIL, timestamp=IN_RANGE)
    _report_event(session, timestamp=BEFORE)
    _report_event(session, timestamp=datetime(2025, 2, 28, 23, 59, 59, tzinfo=UTC))

    events = list(AuditTrailRepositoryAdapter(session).iter_report_events(FROM, BEFORE))

    assert events == [
        AuditTrailEvent(
            occurred_at=FROM,
            event_reference="EVT-AUD-002",
            username="assurance@example.com",
            event_data={"report_name": "Payment Extract"},
        ),
        AuditTrailEvent(
            occurred_at=IN_RANGE,
            event_reference="EVT-AUD-002",
            username="assurance@example.com",
            event_data={"report_name": "User Audit Trail"},
        ),
    ]
