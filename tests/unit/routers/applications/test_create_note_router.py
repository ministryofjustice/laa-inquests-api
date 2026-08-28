from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from starlette.responses import Response

from app.models.history.index import CreateNoteRequest
from app.routers.applications import create_note
from app.use_cases.exceptions import ApplicationNotFoundError


def test_create_note_calls_use_case_and_returns_no_content():
    use_case = MagicMock()
    request = CreateNoteRequest.model_validate({"noteText": "Case note"})

    response = create_note("12345", request=request, use_case=use_case)

    use_case.execute.assert_called_once_with("12345", "Case note")
    assert isinstance(response, Response)
    assert response.status_code == 204
    assert response.body == b""


def test_create_note_returns_not_found_when_application_does_not_exist():
    use_case = MagicMock()
    use_case.execute.side_effect = ApplicationNotFoundError()
    request = CreateNoteRequest(note_text="Case note")

    with pytest.raises(HTTPException) as exception:
        create_note("99999", request=request, use_case=use_case)

    assert exception.value.status_code == 404
    assert exception.value.detail == "Application not found"
