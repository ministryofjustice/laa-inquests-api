from unittest.mock import MagicMock

from fastapi import HTTPException
import pytest

from app.routers.applications import retrieve_coroners_letter


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
    use_case = MagicMock()
    use_case.execute.return_value = MagicMock(content=iter([]), file_name=letter)

    response = retrieve_coroners_letter("1", use_case=use_case)
    assert response.media_type == expected_media_type


def test_retrieve_coroners_letter_throws_error_on_unsupported_documents():
    use_case = MagicMock()
    use_case.execute.return_value = MagicMock(
        content=iter([]), file_name="test-document.txt"
    )

    with pytest.raises(HTTPException) as exception:
        retrieve_coroners_letter("1", use_case=use_case)
    assert exception.value.status_code == 415
    assert (
        exception.value.detail
        == "Returned file type is not supported for streaming. Supported file types are: .png, .jpg, .jpeg, .bmp, .pdf"
    )
