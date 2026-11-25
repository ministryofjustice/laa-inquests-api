import pytest
from pydantic import TypeAdapter, ValidationError

from app.models.validated_types import (
    AddressLine,
    CoronersReference,
    CountyName,
    OrganisationName,
    PersonName,
    ProseText,
    RecipientName,
    RelationshipText,
    TownName,
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


class TestAddressLine:
    @pytest.mark.parametrize(
        "value",
        [
            "123 Example Street",
            "Flat 1/2, O'Neill-Court.",
            "Smith & Sons",
            "1A",
            "12",
            "A" * 100,
        ],
    )
    def test_accepts_valid_address_lines(self, value):
        assert validate(AddressLine, value) == value

    def test_accepts_leading_punctuation_when_there_is_a_letter_or_digit_like_the_ui(
        self,
    ):
        assert validate(AddressLine, "-1 Street") == "-1 Street"

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            (" 1 High Street ", "1 High Street"),
            ("1 High Street\n", "1 High Street"),
            ("O\u2019Neill Court", "O'Neill Court"),
        ],
    )
    def test_trims_and_folds_curly_apostrophes(self, value, expected):
        assert validate(AddressLine, value) == expected

    @pytest.mark.parametrize("character", [c for c in DANGEROUS_CHARACTERS if c != "&"])
    def test_rejects_dangerous_characters(self, character):
        with pytest.raises(ValidationError):
            validate(AddressLine, f"1 Example{character}Street")

    @pytest.mark.parametrize(
        "value",
        ["", " ", "1", "A", "--", "'.", "&&", "1 High\nStreet", "1 Str\x00eet"],
    )
    def test_rejects_too_short_without_letter_or_digit_and_control_characters(
        self, value
    ):
        with pytest.raises(ValidationError):
            validate(AddressLine, value)

    def test_rejects_letters_the_ui_does_not_accept(self):
        with pytest.raises(ValidationError):
            validate(AddressLine, "1 Café Lane")

    def test_rejects_more_than_100_characters(self):
        with pytest.raises(ValidationError):
            validate(AddressLine, "A" * 101)

    @pytest.mark.parametrize("value", [None, 123])
    def test_rejects_non_string_input(self, value):
        with pytest.raises(ValidationError):
            validate(AddressLine, value)


class TestTownName:
    @pytest.mark.parametrize(
        "value",
        ["London", "Stoke-on-Trent", "King's Lynn", "St Albans", "Ab", "A" * 100],
    )
    def test_accepts_valid_town_names(self, value):
        assert validate(TownName, value) == value

    @pytest.mark.parametrize(
        ("value", "expected"),
        [(" London\n", "London"), ("King\u2019s Lynn", "King's Lynn")],
    )
    def test_trims_and_folds_curly_apostrophes(self, value, expected):
        assert validate(TownName, value) == expected

    @pytest.mark.parametrize(
        "value",
        [
            "London1",
            "<Test>",
            "Lon;don",
            "Lon.don",
            "Lon,don",
            "Lon&don",
            "Café",
            "Lon\ndon",
            "",
            " ",
            "A",
            "--",
            "'",
            "A" * 101,
        ],
    )
    def test_rejects_everything_else(self, value):
        with pytest.raises(ValidationError):
            validate(TownName, value)


class TestCountyName:
    @pytest.mark.parametrize(
        "value", ["Kent", "Greater London", "Ayr", "Tyne-and-Wear", "A" * 50]
    )
    def test_accepts_valid_county_names(self, value):
        assert validate(CountyName, value) == value

    def test_trims(self):
        assert validate(CountyName, " Kent\n") == "Kent"

    @pytest.mark.parametrize(
        "value", ["Kent1", "<Test>", "Ke", "", " ", "---", "Kent\nShire", "A" * 51]
    )
    def test_rejects_everything_else(self, value):
        with pytest.raises(ValidationError):
            validate(CountyName, value)


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


class TestRecipientName:
    @pytest.mark.parametrize(
        "value",
        [
            "Smith & Co. Solicitors, Ltd",
            "O'Brien-Jones",
            "Siân Jones",
            "Acme 24 Ltd",
            "J",
            "A" * 100,
        ],
    )
    def test_accepts_person_and_organisation_names(self, value):
        assert validate(RecipientName, value) == value

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            (" Smith & Co. ", "Smith & Co."),
            ("Smith & Co.\n", "Smith & Co."),
            ("O\u2019Brien & Sons", "O'Brien & Sons"),
            ("Jose\u0301 & Co", "Jos\u00e9 & Co"),
        ],
    )
    def test_trims_folds_curly_apostrophes_and_composes_accents(self, value, expected):
        assert validate(RecipientName, value) == expected

    @pytest.mark.parametrize(
        "character",
        [c for c in DANGEROUS_CHARACTERS if c != "&"] + ["/", "@", "+", "_"],
    )
    def test_rejects_characters_outside_the_allow_list(self, character):
        with pytest.raises(ValidationError):
            validate(RecipientName, f"Smith{character}Co")

    @pytest.mark.parametrize(
        "value", ["", " ", "&&", "--", "...", "Smith\nCo", "Smith\x00Co", "A" * 101]
    )
    def test_rejects_empty_without_letter_or_digit_control_characters_and_too_long(
        self, value
    ):
        with pytest.raises(ValidationError):
            validate(RecipientName, value)

    @pytest.mark.parametrize("value", [None, 123])
    def test_rejects_non_string_input(self, value):
        with pytest.raises(ValidationError):
            validate(RecipientName, value)


class TestOrganisationName:
    @pytest.mark.parametrize(
        "value",
        [
            "Test Council",
            "Hammersmith & Fulham Council",
            "St. Mary's Trust, Ltd",
            "A" * 100,
        ],
    )
    def test_accepts_organisation_names(self, value):
        assert validate(OrganisationName, value) == value

    @pytest.mark.parametrize("value", ["", " ", "\n"])
    def test_accepts_empty_and_treats_whitespace_only_as_empty(self, value):
        assert validate(OrganisationName, value) == ""

    def test_trims(self):
        assert validate(OrganisationName, " Test Council\n") == "Test Council"

    @pytest.mark.parametrize(
        "value",
        [
            "<script>",
            "Council;",
            'He said "no"',
            "Co/Ltd",
            "&&",
            "Test\nCouncil",
            "A" * 101,
        ],
    )
    def test_rejects_everything_else(self, value):
        with pytest.raises(ValidationError):
            validate(OrganisationName, value)


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
