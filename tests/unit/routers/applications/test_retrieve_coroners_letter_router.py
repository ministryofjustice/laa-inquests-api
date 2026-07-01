from unittest.mock import MagicMock

from fastapi import HTTPException
import pytest

from app.routers.applications import retrieve_coroners_letter
from app.use_cases.exceptions import (
    CoronersLetterNotFoundError,
    CoronersLetterRetrievalError,
    InvalidCoronersLetterDocumentIdError,
)


def _mock_use_case_with_file(file_name: str):
    use_case = MagicMock()
    use_case.execute.return_value = MagicMock(content=iter([]), file_name=file_name)
    return use_case


def _mock_use_case_raises_exception(exception):
    use_case = MagicMock()
    use_case.execute.side_effect = exception
    return use_case


def test_retrieve_coroners_letter_passes_laa_reference_to_use_case():
    use_case = _mock_use_case_with_file("test-document.pdf")
    laa_reference = "1"

    retrieve_coroners_letter(laa_reference, use_case=use_case)

    use_case.execute.assert_called_once_with(laa_reference)


@pytest.mark.parametrize(
    "letter, expected_media_type",
    [
        ("test-document.png", "image/png"),
        ("test-document.pdf", "application/pdf"),
        ("test-document.jpg", "image/jpeg"),
        ("test-document.jpeg", "image/jpeg"),
        ("test-document.bmp", "image/bmp"),
    ],
)
def test_retrieve_coroners_letter_sets_media_type(letter, expected_media_type):
    use_case = _mock_use_case_with_file(letter)

    response = retrieve_coroners_letter("1", use_case=use_case)
    assert response.media_type == expected_media_type


def test_retrieve_coroners_letter_throws_error_on_unsupported_documents():
    use_case = _mock_use_case_with_file("test-document.txt")

    with pytest.raises(HTTPException) as exception:
        retrieve_coroners_letter("1", use_case=use_case)
    assert exception.value.status_code == 415
    assert (
        exception.value.detail
        == "Returned file type is not supported for streaming. Supported file types are: .png, .jpg, .jpeg, .bmp, .pdf"
    )


def test_retrieve_coroners_letter_returns_400_on_coroners_letter_not_found_error():
    use_case = _mock_use_case_raises_exception(InvalidCoronersLetterDocumentIdError())

    with pytest.raises(HTTPException) as exception:
        retrieve_coroners_letter("1", use_case=use_case)
    assert exception.value.status_code == 400
    assert exception.value.detail == "Invalid coroners letter document id"


def test_retrieve_coroners_letter_returns_404_on_coroners_letter_not_found_error():
    use_case = _mock_use_case_raises_exception(CoronersLetterNotFoundError())

    with pytest.raises(HTTPException) as exception:
        retrieve_coroners_letter("1", use_case=use_case)
    assert exception.value.status_code == 404
    assert exception.value.detail == "Coroners letter not found"


def test_retrieve_coroners_letter_returns_500_on_coroners_letter_retrieval_error():
    use_case = _mock_use_case_raises_exception(CoronersLetterRetrievalError())

    with pytest.raises(HTTPException) as exception:
        retrieve_coroners_letter("1", use_case=use_case)
    assert exception.value.status_code == 500
    assert exception.value.detail == "Failed to retrieve coroners letter"
