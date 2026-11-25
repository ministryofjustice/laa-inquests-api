import pytest
from pydantic import TypeAdapter, ValidationError

from app.models.validated_types import (
    AddressText,
    CoronersReference,
    PersonName,
    ProseText,
    RelationshipText,
)

DANGEROUS_CHARACTERS = ["<", ">", ";", '"', "=", "&", "{", "}", "(", ")", "!", "\\"]
UNICODE_NAMES = ["Siân", "Gŵyn", "Zoë", "José", "Łukasz", "Müller", "Nguyễn", "Søren"]


def validate(annotated_type, value):
    return TypeAdapter(annotated_type).validate_python(value)


class TestPersonName:
    @pytest.mark.parametrize(
        "value", ["Jane", "O'Donald", "Mary-Jane", "De Souza", "a", "A" * 100]
    )
    def test_accepts_valid_names(self, value):
        assert validate(PersonName, value) == value

    @pytest.mark.parametrize("value", UNICODE_NAMES)
    def test_accepts_unicode_letters(self, value):
        assert validate(PersonName, value) == value

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ("  Jane  ", "Jane"),
            ("Jane\n", "Jane"),
            ("\tJane\r\n", "Jane"),
            ("\u00a0Jane\u00a0", "Jane"),
            ("O\u2019Brien", "O'Brien"),
            ("O\u2018Brien", "O'Brien"),
            ("Jose\u0301", "Jos\u00e9"),
        ],
    )
    def test_trims_folds_curly_apostrophes_and_composes_before_checking(
        self, value, expected
    ):
        assert validate(PersonName, value) == expected

    @pytest.mark.parametrize("character", DANGEROUS_CHARACTERS)
    def test_rejects_dangerous_characters(self, character):
        with pytest.raises(ValidationError):
            validate(PersonName, f"Jane{character}Smith")

    @pytest.mark.parametrize(
        "value",
        ["Jane1", "Jane.", "Jane,", "Jane/Smith", "Jane_Smith", "Jane\u200b"],
    )
    def test_rejects_characters_outside_allow_list(self, value):
        with pytest.raises(ValidationError):
            validate(PersonName, value)

    @pytest.mark.parametrize(
        "value", ["", " ", "-Smith", "'Smith", "\u0301", "\u0301Smith"]
    )
    def test_rejects_empty_non_letter_start_and_bare_combining_marks(self, value):
        with pytest.raises(ValidationError):
            validate(PersonName, value)

    def test_rejects_more_than_100_characters(self):
        with pytest.raises(ValidationError):
            validate(PersonName, "A" * 101)

    @pytest.mark.parametrize("value", ["Ja\nne", "Ja\tne", "Jane\x00", "Ja\x00ne"])
    def test_rejects_embedded_newlines_and_control_characters(self, value):
        with pytest.raises(ValidationError):
            validate(PersonName, value)

    @pytest.mark.parametrize("value", [None, 123, ["Jane"]])
    def test_rejects_non_string_input(self, value):
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

    @pytest.mark.parametrize(
        ("value", "expected"),
        [(" COR-1 ", "COR-1"), ("COR-1\n", "COR-1"), (" ", ""), ("\n", "")],
    )
    def test_trims_and_treats_whitespace_only_as_not_provided(self, value, expected):
        assert validate(CoronersReference, value) == expected

    @pytest.mark.parametrize("character", DANGEROUS_CHARACTERS + ["'", ","])
    def test_rejects_characters_outside_allow_list(self, character):
        with pytest.raises(ValidationError):
            validate(CoronersReference, f"COR{character}123")

    @pytest.mark.parametrize("value", ["-123", "/123", "CO\nR"])
    def test_rejects_bad_start_and_embedded_newline(self, value):
        with pytest.raises(ValidationError):
            validate(CoronersReference, value)

    def test_rejects_more_than_50_characters(self):
        with pytest.raises(ValidationError):
            validate(CoronersReference, "A" * 51)


class TestRelationshipText:
    @pytest.mark.parametrize(
        "value", ["", "Son", "O'Donald", "Step-parent", "Nièce", "A" * 70]
    )
    def test_accepts_names_and_empty_string(self, value):
        assert validate(RelationshipText, value) == value

    @pytest.mark.parametrize(
        ("value", "expected"),
        [(" Son ", "Son"), ("Son\n", "Son"), (" ", ""), ("O\u2019Neill", "O'Neill")],
    )
    def test_trims_folds_apostrophes_and_treats_whitespace_only_as_empty(
        self, value, expected
    ):
        assert validate(RelationshipText, value) == expected

    @pytest.mark.parametrize(
        "value", ["-Son", "<Spouse>", "Son1", "So\nn", "\u0301", "A" * 71]
    )
    def test_rejects_everything_else_a_person_name_rejects(self, value):
        with pytest.raises(ValidationError):
            validate(RelationshipText, value)


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
