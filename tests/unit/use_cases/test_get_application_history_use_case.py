from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from app.models.application.index import Application
from app.models.history.enums import ActorType, HistoryEventReference
from app.models.history.index import HistoryEvent, HistoryEventResponse
from app.models.notifications.enums import NotificationType
from app.use_cases.exceptions import ApplicationNotFoundError
from app.use_cases.get_application_history import GetApplicationHistoryUseCase


def _make_use_case(
    application: Application | None = None,
    history_events: list[HistoryEvent] | None = None,
) -> GetApplicationHistoryUseCase:
    get_application_history_port = MagicMock()
    get_application_history_port.get_application_history.return_value = (
        history_events if history_events is not None else []
    )
    get_application_port = MagicMock()
    get_application_port.get_application_by_laa_reference.return_value = (
        application if application is not None else None
    )
    return GetApplicationHistoryUseCase(
        get_application_history_port=get_application_history_port,
        get_application_port=get_application_port,
    )


def test_execute_returns_empty_list_when_no_matching_events():
    use_case = _make_use_case(application=MagicMock())

    assert use_case.execute("1") == []


def test_execute_raises_application_not_found_error_when_no_matching_application_found():
    use_case = _make_use_case(history_events=[])

    with pytest.raises(ApplicationNotFoundError):
        use_case.execute("1")


def test_execute_returns_history_events_from_port():
    history_event_1 = HistoryEvent(
        id=1,
        event_reference=HistoryEventReference.APPLICATION_SUBMITTED,
        timestamp=datetime.now(UTC),
        actor="provider@example.com",
        actor_type=ActorType.PROVIDER,
        event_data=None,
        laa_reference=123456,
    )
    history_event_2 = HistoryEvent(
        id=2,
        event_reference=HistoryEventReference.APPLICATION_ASSESSMENT_COMPLETED,
        timestamp=datetime.now(UTC),
        actor="caseworker@justice.gov.uk",
        actor_type=ActorType.CASEWORKER,
        event_data={"context": "Test data", "related_link": "/get-certificate/123456"},
        laa_reference=123456,
    )
    use_case = _make_use_case(
        application=MagicMock(), history_events=[history_event_1, history_event_2]
    )

    result = use_case.execute("1")

    assert len(result) == 2
    assert all(isinstance(event, HistoryEventResponse) for event in result)
    assert result[0].actor == "Provider"
    assert result[0].event_reference == HistoryEventReference.APPLICATION_SUBMITTED
    assert result[0].event_data is None
    assert result[1].actor == "caseworker@justice.gov.uk"
    assert (
        result[1].event_reference
        == HistoryEventReference.APPLICATION_ASSESSMENT_COMPLETED
    )
    assert result[1].event_data["context"] == "Test data"
    assert result[1].event_data["related_link"] == "/get-certificate/123456"


def test_execute_masks_provider_actor_as_provider():
    history_event = HistoryEvent(
        id=1,
        event_reference=HistoryEventReference.APPLICATION_SUBMITTED,
        timestamp=datetime.now(UTC),
        actor="provider@example.com",
        actor_type=ActorType.PROVIDER,
        event_data=None,
        laa_reference=123456,
    )
    use_case = _make_use_case(application=MagicMock(), history_events=[history_event])

    result = use_case.execute("1")

    assert result[0].actor == "Provider"


def test_execute_masks_recipient_in_event_data():
    history_event = HistoryEvent(
        id=1,
        event_reference=HistoryEventReference.CLAIM_SUBMISSION_CONFIRMATION,
        timestamp=datetime.now(UTC),
        actor=ActorType.SYSTEM,
        actor_type=ActorType.SYSTEM,
        event_data={
            "recipient": "recipient@example.com",
            "channel": NotificationType.EMAIL,
        },
        laa_reference=123456,
    )
    use_case = _make_use_case(application=MagicMock(), history_events=[history_event])

    result = use_case.execute("1")

    assert "recipient" not in result[0].event_data
    assert result[0].event_data["channel"] == NotificationType.EMAIL


def test_execute_preserves_non_provider_actor():
    history_event = HistoryEvent(
        id=1,
        event_reference=HistoryEventReference.APPLICATION_ASSESSMENT_COMPLETED,
        timestamp=datetime.now(UTC),
        actor="caseworker@justice.gov.uk",
        actor_type=ActorType.CASEWORKER,
        event_data=None,
        laa_reference=123456,
    )
    use_case = _make_use_case(application=MagicMock(), history_events=[history_event])

    result = use_case.execute("1")

    assert result[0].actor == "caseworker@justice.gov.uk"
