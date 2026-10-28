from datetime import UTC, datetime

import pytest

from app.domain.audit_trail import (
    AuditTrailEvent,
    application_certificate_view_event,
    application_overview_view_event,
    csv_safe,
    history_event,
    report_download_event,
    resolve_history_username,
)
from app.models.audit.enums import ReportType
from app.models.history.enums import ActorType


@pytest.mark.parametrize("character", ["=", "+", "-", "@", "\t", "\r"])
def test_csv_safe_prefixes_values_that_could_be_read_as_formulas(character):
    assert csv_safe(f"{character}cmd") == f"'{character}cmd"


@pytest.mark.parametrize(
    "value", ["", "provider@example.com", "Application received", "15-03-2025", "a=b"]
)
def test_csv_safe_leaves_other_values_unchanged(value):
    assert csv_safe(value) == value


def test_provider_username_is_the_stored_actor_email():
    username = resolve_history_username(
        ActorType.PROVIDER, "provider@example.com", actor_email_address=None
    )

    assert username == "provider@example.com"


def test_caseworker_username_is_the_actor_email_address():
    username = resolve_history_username(
        ActorType.CASEWORKER, "Test Name", actor_email_address="caseworker@example.com"
    )

    assert username == "caseworker@example.com"


def test_caseworker_username_falls_back_to_the_stored_name_when_no_email_was_recorded():
    username = resolve_history_username(
        ActorType.CASEWORKER, "Test Name", actor_email_address=None
    )

    assert username == "Test Name"


def test_caseworker_username_falls_back_to_the_stored_name_for_an_empty_email():
    username = resolve_history_username(
        ActorType.CASEWORKER, "Test Name", actor_email_address=""
    )

    assert username == "Test Name"


@pytest.mark.parametrize("actor", ["System", ActorType.SYSTEM, "anything"])
def test_system_username_is_system(actor):
    username = resolve_history_username(
        ActorType.SYSTEM, actor, actor_email_address=None
    )

    assert username == "System"


OCCURRED_AT = datetime(2025, 3, 15, 12, 0, tzinfo=UTC)


def _history_event(actor_type: ActorType, **overrides) -> AuditTrailEvent:
    values = {
        "occurred_at": OCCURRED_AT,
        "event_reference": "EVT-BUS-APP-001",
        "actor_type": actor_type,
        "actor": "provider@example.com",
        "actor_email_address": None,
        "laa_reference": "INQ-123-456",
        "firm_code": "0A123B",
        "office_id": "0U651L",
        "event_data": {"key": "value"},
    }
    return history_event(**(values | overrides))


def test_provider_history_event_includes_firm_details():
    event = _history_event(ActorType.PROVIDER)

    assert event == AuditTrailEvent(
        occurred_at=OCCURRED_AT,
        event_reference="EVT-BUS-APP-001",
        username="provider@example.com",
        laa_reference="INQ-123-456",
        firm_code="0A123B",
        office_id="0U651L",
        event_data={"key": "value"},
    )


@pytest.mark.parametrize("actor_type", [ActorType.CASEWORKER, ActorType.SYSTEM])
def test_history_event_for_other_actors_has_no_firm_details(actor_type):
    event = _history_event(actor_type)

    assert event.firm_code is None
    assert event.office_id is None
    assert event.laa_reference == "INQ-123-456"


def test_application_overview_view_event_is_reported_as_application_viewed():
    event = application_overview_view_event(
        OCCURRED_AT, "caseworker@example.com", "INQ-123-456"
    )

    assert event == AuditTrailEvent(
        occurred_at=OCCURRED_AT,
        event_reference="EVT-AUD-001",
        username="caseworker@example.com",
        laa_reference="INQ-123-456",
    )


def test_application_certificate_view_event_is_reported_as_certificate_viewed():
    event = application_certificate_view_event(
        OCCURRED_AT, "caseworker@example.com", "INQ-123-456"
    )

    assert event == AuditTrailEvent(
        occurred_at=OCCURRED_AT,
        event_reference="EVT-AUD-002",
        username="caseworker@example.com",
        laa_reference="INQ-123-456",
    )


def test_report_download_event_carries_the_report_name():
    event = report_download_event(
        OCCURRED_AT, "assurance@example.com", ReportType.PAYMENT_EXTRACT
    )

    assert event == AuditTrailEvent(
        occurred_at=OCCURRED_AT,
        event_reference="EVT-AUD-003",
        username="assurance@example.com",
        event_data={"report_name": "Payment Extract"},
    )
