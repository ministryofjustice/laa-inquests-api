from datetime import date
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from starlette.responses import Response

from app.models.application.index import GrantApplicationUpdate
from app.routers.applications import grant_decision
from app.use_cases.exceptions import ApplicationNotFoundError, ProceedingsNotFoundError


def _grant_request() -> GrantApplicationUpdate:
    return GrantApplicationUpdate(certificate_start_date=date(2000, 1, 1))


def test_grant_decision_calls_use_case_with_expected_arguments():
    use_case = MagicMock()
    request = _grant_request()

    grant_decision("1", request=request, use_case=use_case)

    use_case.execute.assert_called_once_with("1", request)


def test_grant_decision_returns_204_on_success():
    use_case = MagicMock()

    response = grant_decision("1", request=_grant_request(), use_case=use_case)

    assert isinstance(response, Response)
    assert response.status_code == 204


def test_grant_decision_raises_404_when_application_not_found():
    use_case = MagicMock()
    use_case.execute.side_effect = ApplicationNotFoundError()

    with pytest.raises(HTTPException) as exception:
        grant_decision("1", request=_grant_request(), use_case=use_case)

    assert exception.value.status_code == 404
    assert exception.value.detail == "Application not found"


def test_grant_decision_raises_404_when_no_proceedings_found():
    use_case = MagicMock()
    use_case.execute.side_effect = ProceedingsNotFoundError()

    with pytest.raises(HTTPException) as exception:
        grant_decision("1", request=_grant_request(), use_case=use_case)

    assert exception.value.status_code == 404
    assert exception.value.detail == "No proceedings found for application"
