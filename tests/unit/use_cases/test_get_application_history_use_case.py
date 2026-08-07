from unittest.mock import MagicMock

import pytest

from app.models.application.index import Application
from app.models.history.index import HistoryEvent
from app.use_cases.exceptions import ApplicationNotFoundError
from app.use_cases.get_application_history import GetApplicationHistoryUseCase


# TODO: change for the history_events to be list[HistoryEventResponse], e.g. with provider email removed
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
    history_event_1 = MagicMock(spec=HistoryEvent)
    history_event_2 = MagicMock(spec=HistoryEvent)
    use_case = _make_use_case(
        application=MagicMock(), history_events=[history_event_1, history_event_2]
    )

    result = use_case.execute("1")

    assert result == [history_event_1, history_event_2]
