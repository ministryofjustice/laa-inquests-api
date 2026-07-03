from unittest.mock import MagicMock
from fastapi import HTTPException
from starlette.responses import Response

import pytest

from app.routers.applications import grant_decision
from app.use_cases.exceptions import ApplicationNotFoundError, ProceedingsNotFoundError


def test_grant_decision_calls_use_case_with_expected_arguments():
    use_case = MagicMock()

    grant_decision("1", use_case=use_case)

    use_case.execute.assert_called_once_with("1")


def test_grant_decision_returns_204_on_success():
    use_case = MagicMock()

    response = grant_decision("1", use_case=use_case)

    assert isinstance(response, Response)
    assert response.status_code == 204


def test_grant_decision_raises_404_when_application_not_found():
    use_case = MagicMock()
    use_case.execute.side_effect = ApplicationNotFoundError()

    with pytest.raises(HTTPException) as exception:
        grant_decision("1", use_case=use_case)

    assert exception.value.status_code == 404
    assert exception.value.detail == "Application not found"


def test_grant_decision_raises_404_when_no_proceedings_found():
    use_case = MagicMock()
    use_case.execute.side_effect = ProceedingsNotFoundError()

    with pytest.raises(HTTPException) as exception:
        grant_decision("1", use_case=use_case)

    assert exception.value.status_code == 404
    assert exception.value.detail == "No proceedings found for application"
