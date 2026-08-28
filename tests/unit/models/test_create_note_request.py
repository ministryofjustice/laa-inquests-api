import pytest
from pydantic import ValidationError

from app.models.history.index import CreateNoteRequest


def test_create_note_request_accepts_camel_case_and_preserves_text():
    request = CreateNoteRequest.model_validate({"noteText": "  Case note  "})

    assert request.note_text == "  Case note  "
    assert request.model_dump(by_alias=True) == {"noteText": "  Case note  "}


def test_create_note_request_accepts_10_000_characters():
    note_text = "a" * 10_000

    request = CreateNoteRequest(note_text=note_text)

    assert request.note_text == note_text


@pytest.mark.parametrize(
    "note_text",
    [
        "",
        " \t\n",
        "a" * 10_001,
    ],
)
def test_create_note_request_rejects_invalid_text(note_text):
    with pytest.raises(ValidationError):
        CreateNoteRequest(note_text=note_text)
