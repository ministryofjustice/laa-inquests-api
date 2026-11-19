import pytest

from app.domain.file_name import MAX_FILE_NAME_LENGTH, is_valid_upload_file_name


@pytest.mark.parametrize(
    "file_name",
    [
        "letter.pdf",
        "Coroners letter (1).pdf",
        "Jane Doe - letter_2024!.pdf",
        "a" * (MAX_FILE_NAME_LENGTH - 4) + ".pdf",
    ],
)
def test_accepts_names_using_only_allowed_characters(file_name):
    assert is_valid_upload_file_name(file_name) is True


@pytest.mark.parametrize(
    "file_name",
    [
        None,
        "",
        "<img src=x onerror=alert(1)>.pdf",
        'letter".pdf',
        "letter'.pdf",
        "letter\\evil.pdf",
        "folder/letter.pdf",
        "letter\x00.pdf",
        "letter\t.pdf",
        "letter.pdf\n",
        "letter\r\nX-Injected: 1.pdf",
        "\uff1cscript\uff1e.pdf",
        "lettér.pdf",
        "a" * (MAX_FILE_NAME_LENGTH - 3) + ".pdf",
    ],
)
def test_rejects_names_with_other_characters_or_wrong_length(file_name):
    assert is_valid_upload_file_name(file_name) is False
