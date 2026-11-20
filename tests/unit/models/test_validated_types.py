import pytest
from pydantic import TypeAdapter, ValidationError

from app.models.validated_types import (
    AddressText,
    CoronersReference,
    PersonName,
    PersonNameOrEmpty,
    ProseText,
)

DANGEROUS_CHARACTERS = ["<", ">", ";", '"', "=", "&", "{", "}", "(", ")", "!", "\\"]


def validate(annotated_type, value):
    return TypeAdapter(annotated_type).validate_python(value)


class TestPersonName:
    @pytest.mark.parametrize(
        "value", ["Jane", "O'Donald", "Mary-Jane", "De Souza", "a", "A" * 50]
    )
    def test_accepts_valid_names(self, value):
        assert validate(PersonName, value) == value

    @pytest.mark.parametrize("character", DANGEROUS_CHARACTERS)
    def test_rejects_dangerous_characters(self, character):
        with pytest.raises(ValidationError):
            validate(PersonName, f"Jane{character}Smith")

    @pytest.mark.parametrize(
        "value",
        ["Jane1", "Zoë", "Jane.", "Jane,", "Jane/Smith", "Jane_Smith", "Jane\u200b"],
    )
    def test_rejects_characters_outside_allow_list(self, value):
        with pytest.raises(ValidationError):
            validate(PersonName, value)

    @pytest.mark.parametrize("value", ["", " ", "-Smith", "'Smith", " Smith"])
    def test_rejects_empty_or_non_letter_start(self, value):
        with pytest.raises(ValidationError):
            validate(PersonName, value)

    def test_rejects_more_than_50_characters(self):
        with pytest.raises(ValidationError):
            validate(PersonName, "A" * 51)

    @pytest.mark.parametrize(
        "value", ["Jane\n", "Jane\r\n", "Ja\nne", "Jane\t", "Jane\x00"]
    )
    def test_rejects_newlines_and_control_characters(self, value):
        with pytest.raises(ValidationError):
            validate(PersonName, value)


class TestAddressText:
    @pytest.mark.parametrize(
        "value",
        [
            "123 Example Street",
            "Flat 1/2, O'Neill-Court.",
            "1",
            "A" * 50,
        ],
    )
    def test_accepts_valid_addresses(self, value):
        assert validate(AddressText, value) == value

    @pytest.mark.parametrize("character", DANGEROUS_CHARACTERS)
    def test_rejects_dangerous_characters(self, character):
        with pytest.raises(ValidationError):
            validate(AddressText, f"1 Example{character}Street")

    @pytest.mark.parametrize(
        "value",
        ["", " ", "-1 Street", ".1 Street", "'1 Street", "1 Street\n", "1 Str\x00eet"],
    )
    def test_rejects_empty_bad_start_and_control_characters(self, value):
        with pytest.raises(ValidationError):
            validate(AddressText, value)

    def test_rejects_more_than_50_characters(self):
        with pytest.raises(ValidationError):
            validate(AddressText, "A" * 51)


class TestCoronersReference:
    @pytest.mark.parametrize(
        "value", ["", "COR-2025-123", "2025/123.A", "Example reference 1", "A" * 50]
    )
    def test_accepts_valid_references_and_empty_string(self, value):
        assert validate(CoronersReference, value) == value

    @pytest.mark.parametrize("character", DANGEROUS_CHARACTERS + ["'", ","])
    def test_rejects_characters_outside_allow_list(self, character):
        with pytest.raises(ValidationError):
            validate(CoronersReference, f"COR{character}123")

    @pytest.mark.parametrize("value", [" ", "-123", "/123", "COR-1\n", "\n"])
    def test_rejects_whitespace_only_bad_start_and_trailing_newline(self, value):
        with pytest.raises(ValidationError):
            validate(CoronersReference, value)

    def test_rejects_more_than_50_characters(self):
        with pytest.raises(ValidationError):
            validate(CoronersReference, "A" * 51)


class TestPersonNameOrEmpty:
    @pytest.mark.parametrize("value", ["", "Son", "O'Donald", "Mary-Jane", "A" * 50])
    def test_accepts_names_and_empty_string(self, value):
        assert validate(PersonNameOrEmpty, value) == value

    @pytest.mark.parametrize(
        "value", [" ", "\n", "Son\n", "-Son", "<Spouse>", "Son1", "A" * 51]
    )
    def test_rejects_everything_else_a_person_name_rejects(self, value):
        with pytest.raises(ValidationError):
            validate(PersonNameOrEmpty, value)


class TestProseText:
    @pytest.mark.parametrize(
        "value",
        [
            "Plain sentence.",
            'It\'s "quoted"; with = & ( ) { } -- punctuation!',
            "Line one\nLine two\r\nLine three\twith tab",
            "Zoë café – unicode is fine in prose",
            "A" * 20_000,
        ],
    )
    def test_accepts_prose(self, value):
        assert validate(ProseText, value) == value

    @pytest.mark.parametrize("value", ["<script>", "a > b", "<", ">"])
    def test_rejects_angle_brackets(self, value):
        with pytest.raises(ValidationError):
            validate(ProseText, value)

    @pytest.mark.parametrize(
        "value", ["a\x00b", "a\x07b", "a\x1bb", "a\x7fb", "a\u200bb", "a\u202eb"]
    )
    def test_rejects_control_and_format_characters(self, value):
        with pytest.raises(ValidationError):
            validate(ProseText, value)
