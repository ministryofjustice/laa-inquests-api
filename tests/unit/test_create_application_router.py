import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.models.application.index import CoronersLetterResponse
from app.routers.applications import create_application, upload_coroners_letter
from app.use_cases.exceptions import CoronersLetterSaveError


def _make_request():
    request = MagicMock()
    request.coroners_letter_id = "test-file_abc123.pdf"
    return request


def test_create_application_calls_create_use_case():
    request = _make_request()
    create_use_case = MagicMock()

    create_application(request, create_use_case=create_use_case)

    create_use_case.execute.assert_called_once_with(request)


# upload_coroners_letter tests


def _make_upload_file(content: bytes = b"pdf content", filename: str = "letter.pdf"):
    mock_file = MagicMock()
    mock_file.filename = filename
    mock_file.read = AsyncMock(return_value=content)
    return mock_file


def _make_sds_response() -> CoronersLetterResponse:
    return CoronersLetterResponse(
        id="test-file_abc123.pdf", status=201, file_name="test-file_abc123.pdf"
    )


def test_upload_coroners_letter_returns_file_id():
    use_case = MagicMock()
    use_case.execute.return_value = _make_sds_response()

    result = asyncio.run(
        upload_coroners_letter(file=_make_upload_file(), use_case=use_case)
    )

    assert result.file_id == "test-file_abc123.pdf"


def test_upload_coroners_letter_returns_500_when_sds_fails():
    use_case = MagicMock()
    use_case.execute.side_effect = CoronersLetterSaveError("SDS failed")

    with pytest.raises(HTTPException) as exc:
        asyncio.run(upload_coroners_letter(file=_make_upload_file(), use_case=use_case))

    assert exc.value.status_code == 500
