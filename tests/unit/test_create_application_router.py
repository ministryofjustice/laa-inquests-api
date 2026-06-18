from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.models.application.index import CoronersLetterCreate
from app.routers.applications import create_application
from app.use_cases.exceptions import CoronersLetterSaveError


def _make_request():
    request = MagicMock()
    request.coroners_letter = CoronersLetterCreate(
        coroners_letter=b"test content",
        file_name="letter.pdf",
    )
    return request


def test_create_application_calls_save_letter_then_create():
    request = _make_request()
    save_letter_use_case = MagicMock()
    create_use_case = MagicMock()

    create_application(
        request,
        save_letter_use_case=save_letter_use_case,
        create_use_case=create_use_case,
    )

    save_letter_use_case.execute.assert_called_once()
    create_use_case.execute.assert_called_once_with(request)


def test_create_application_returns_500_and_does_not_create_when_letter_save_fails():
    request = _make_request()
    save_letter_use_case = MagicMock()
    save_letter_use_case.execute.side_effect = CoronersLetterSaveError("SDS failed")
    create_use_case = MagicMock()

    with pytest.raises(HTTPException) as exc:
        create_application(
            request,
            save_letter_use_case=save_letter_use_case,
            create_use_case=create_use_case,
        )

    assert exc.value.status_code == 500
    create_use_case.execute.assert_not_called()
