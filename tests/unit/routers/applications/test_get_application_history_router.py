from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.models.history.enums import HistoryEventReference
from app.models.history.index import HistoryEventResponse
from app.routers.applications import get_application_history
from app.use_cases.exceptions import ApplicationNotFoundError


def test_get_application_history_calls_use_case_with_the_laa_reference():
    use_case = MagicMock()
    mock_response = HistoryEventResponse(
        timestamp=datetime.now(UTC),
        actor="provider@example.com",
        event_reference=HistoryEventReference.APPLICATION_SUBMITTED,
        event_data=None,
    )
    use_case.execute.return_value = [mock_response]

    get_application_history("1", use_case=use_case)

    use_case.execute.assert_called_once_with("1")


def test_get_application_history_returns_empty_list_when_use_case_returns_empty():
    use_case = MagicMock()
    use_case.execute.return_value = []

    result = get_application_history("1", use_case=use_case)

    assert result == []


def test_get_application_history_raises_404_when_application_not_found():
    use_case = MagicMock()
    use_case.execute.side_effect = ApplicationNotFoundError()

    with pytest.raises(HTTPException) as exception:
        get_application_history("99999", use_case=use_case)

    assert exception.value.status_code == 404
    assert exception.value.detail == "Application not found"
