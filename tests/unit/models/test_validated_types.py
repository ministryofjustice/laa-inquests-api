import pytest
from pydantic import TypeAdapter, ValidationError

from app.models.validated_types import (
    AddressLine,
    ClaimReference,
    CoronersReference,
    CountyName,
    EmailAddress,
    FirmCode,
    FurtherInformation,
    LaaReference,
    Nino,
    OfficeCode,
    OrganisationName,
    PersonName,
    Postcode,
    PreviousReference,
    ProseText,
    RecipientName,
    RefusalJustification,
    RejectionReason,
    RelationshipText,
    SearchReference,
    SingleLineText,
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


class TestNino:
    @pytest.mark.parametrize(
        "value",
        [
            "AA123456A",
            "AB123456C",
            "ab123456c",
            "AB 123456 C",
            "JG123456D",
            "QQ123456C",
        ],
    )
    def test_accepts_valid_numbers_and_keeps_them_as_typed(self, value):
        assert validate(Nino, value) == value

    def test_trims_surrounding_whitespace(self):
        assert validate(Nino, " AB123456C\n") == "AB123456C"

    @pytest.mark.parametrize("letter", ["D", "F", "I", "U", "V"])
    @pytest.mark.parametrize("position", [0, 1])
    def test_rejects_letters_the_ui_excludes_in_either_position(self, letter, position):
        prefix = ["A", "A"]
        prefix[position] = letter

        with pytest.raises(ValidationError):
            validate(Nino, f"{''.join(prefix)}123456A")

    @pytest.mark.parametrize("prefix", ["BG", "GB", "NK", "KN", "TN", "NT", "ZZ", "bg"])
    def test_rejects_the_prefixes_the_ui_excludes(self, prefix):
        with pytest.raises(ValidationError):
            validate(Nino, f"{prefix}123456A")

    @pytest.mark.parametrize(
        "value",
        [
            "AB123456E",
            "AB12345A",
            "AB1234567A",
            "AB123456",
            "A1123456A",
            "AB 12 34 56 C",
            "AB\n123456C",
            "AB\t123456C",
            "ſb123456c",
            "",
            " ",
        ],
    )
    def test_rejects_the_wrong_shape(self, value):
        with pytest.raises(ValidationError):
            validate(Nino, value)

    @pytest.mark.parametrize("value", ["AB123456A<b>", "AB123456A;", "AB123456Ax"])
    def test_rejects_anything_after_the_suffix_letter(self, value):
        with pytest.raises(ValidationError):
            validate(Nino, value)

    @pytest.mark.parametrize("value", [None, 123])
    def test_rejects_non_string_input(self, value):
        with pytest.raises(ValidationError):
            validate(Nino, value)


class TestPostcode:
    @pytest.mark.parametrize(
        "value", ["SW1A 1AA", "M1 1AE", "CR26XH", "EC1A1BB", "AB12 3CD"]
    )
    def test_accepts_valid_postcodes(self, value):
        assert validate(Postcode, value) == value

    @pytest.mark.parametrize(
        ("value", "expected"),
        [("sw1a 1aa", "SW1A 1AA"), (" SW1A 1AA\n", "SW1A 1AA"), ("m11ae", "M11AE")],
    )
    def test_trims_and_uppercases(self, value, expected):
        assert validate(Postcode, value) == expected

    @pytest.mark.parametrize(
        "value",
        [
            "SW1A",
            "SW1A 1AAA1",
            "SW1A-1AA",
            "SW1A,1AA",
            "<b>SW1A",
            "SW1A\n1AA",
            "SW1A\t1AA",
            "",
            " ",
        ],
    )
    def test_rejects_wrong_length_and_characters(self, value):
        with pytest.raises(ValidationError):
            validate(Postcode, value)

    @pytest.mark.parametrize("value", ["ſw1a 1aa", "ı1234", "ß1234"])
    def test_rejects_non_ascii_before_uppercasing_can_turn_it_into_ascii(self, value):
        with pytest.raises(ValidationError):
            validate(Postcode, value)

    @pytest.mark.parametrize("value", [None, 123])
    def test_rejects_non_string_input(self, value):
        with pytest.raises(ValidationError):
            validate(Postcode, value)


class TestPreviousReference:
    @pytest.mark.parametrize(
        "value", ["", "INQ-ABC-DEF", "1234567/A", "Ref 12.3", "A" * 35]
    )
    def test_accepts_references_and_empty_string(self, value):
        assert validate(PreviousReference, value) == value

    @pytest.mark.parametrize(
        ("value", "expected"),
        [(" INQ-ABC-DEF\n", "INQ-ABC-DEF"), (" ", ""), ("\n", "")],
    )
    def test_trims_and_treats_whitespace_only_as_not_provided(self, value, expected):
        assert validate(PreviousReference, value) == expected

    @pytest.mark.parametrize(
        "value", ["<b>", "INQ;ABC", "INQ'ABC", "-INQ", "INQ\nABC", "A" * 36]
    )
    def test_rejects_everything_else(self, value):
        with pytest.raises(ValidationError):
            validate(PreviousReference, value)


class TestOfficeCode:
    @pytest.mark.parametrize(
        "value", ["0U651L", "1A234B", "ABC123", "0u651l", "A", "A" * 20]
    )
    def test_accepts_letters_and_digits(self, value):
        assert validate(OfficeCode, value) == value

    def test_trims(self):
        assert validate(OfficeCode, " 0U651L\n") == "0U651L"

    @pytest.mark.parametrize(
        "value",
        [
            "",
            " ",
            "0U 651L",
            "0U-651L",
            "0U651L<b>",
            "0U651L;",
            "0U\n651L",
            "é0U651L",
            "A" * 21,
        ],
    )
    def test_rejects_everything_else(self, value):
        with pytest.raises(ValidationError):
            validate(OfficeCode, value)

    @pytest.mark.parametrize("value", [None, 123])
    def test_rejects_non_string_input(self, value):
        with pytest.raises(ValidationError):
            validate(OfficeCode, value)


class TestEmailAddress:
    @pytest.mark.parametrize(
        "value",
        [
            "provider@example.com",
            "claimant-123@provider.co.uk",
            "o'brien+tag@firm.co.uk",
            "first.last_firm.com#EXT#@tenant.onmicrosoft.com",
            "a@b.co",
            f"{'a' * 64}@example.com",
        ],
    )
    def test_accepts_mailbox_style_addresses(self, value):
        assert validate(EmailAddress, value) == value

    def test_trims_and_keeps_case(self):
        assert (
            validate(EmailAddress, " Provider@Example.com\n") == "Provider@Example.com"
        )

    @pytest.mark.parametrize(
        "value",
        [
            "provider@example",
            "provider@",
            "@example.com",
            "pro vider@example.com",
            "<b>@example.com",
            "provider@example.com;x",
            'pro"vider@example.com',
            "pro,vider@example.com",
            "pro(vider)@example.com",
            "a@b.c",
            "provider@@example.com",
            "provider@exam_ple.com",
            "provider@-example.com",
            "provider@example-.com",
            "provider@example..com",
            "pr\novider@example.com",
            "pröv@example.com",
            "provider@exämple.com",
            f"{'a' * 65}@example.com",
            f"{'a' * 250}@example.com",
            "",
            " ",
        ],
    )
    def test_rejects_everything_else(self, value):
        with pytest.raises(ValidationError):
            validate(EmailAddress, value)

    @pytest.mark.parametrize("value", [None, 123])
    def test_rejects_non_string_input(self, value):
        with pytest.raises(ValidationError):
            validate(EmailAddress, value)


class TestReferenceParams:
    @pytest.mark.parametrize("annotated_type", [LaaReference, ClaimReference])
    @pytest.mark.parametrize(
        "value",
        ["INQ-ABC-DEF", "INQC-ABCD-EFGH", "99999", "inq-abc-def", "A", "A" * 20],
    )
    def test_accepts_well_formed_references_including_unknown_ones(
        self, annotated_type, value
    ):
        assert validate(annotated_type, value) == value

    @pytest.mark.parametrize("annotated_type", [LaaReference, ClaimReference])
    @pytest.mark.parametrize(
        "value",
        [
            "",
            "INQ ABC",
            "<b>",
            "INQ_ABC",
            "INQ.ABC",
            "INQ-ABC-DEF\n",
            "../x",
            "é",
            "A" * 21,
        ],
    )
    def test_rejects_malformed_references(self, annotated_type, value):
        with pytest.raises(ValidationError):
            validate(annotated_type, value)


class TestFirmCode:
    @pytest.mark.parametrize("value", ["0A123B", "123", "ABC123", "A" * 20])
    def test_accepts_letters_and_digits(self, value):
        assert validate(FirmCode, value) == value

    @pytest.mark.parametrize(
        "value", ["", "a b", "a?b", "a#b", "a.b", "a/b", "a-b", "é", "A" * 21]
    )
    def test_rejects_characters_that_could_alter_the_provider_details_url(self, value):
        with pytest.raises(ValidationError):
            validate(FirmCode, value)


class TestSearchReference:
    @pytest.mark.parametrize(
        "value", ["", "INQ-ABC-DEF", " inq abc def ", "<b>", "A" * 50]
    )
    def test_only_caps_the_length_so_typos_still_search_and_find_nothing(self, value):
        assert validate(SearchReference, value) == value

    def test_rejects_more_than_50_characters(self):
        with pytest.raises(ValidationError):
            validate(SearchReference, "A" * 51)

    @pytest.mark.parametrize("value", [None, 123])
    def test_rejects_non_string_input(self, value):
        with pytest.raises(ValidationError):
            validate(SearchReference, value)


class TestFurtherInformation:
    @pytest.mark.parametrize(
        "value",
        ["", "ab", "Line one\nLine two", 'It\'s "quoted"; fine = & (ok)', "A" * 500],
    )
    def test_accepts_nothing_or_two_to_500_characters(self, value):
        assert validate(FurtherInformation, value) == value

    @pytest.mark.parametrize("value", ["a", "A" * 501])
    def test_rejects_one_character_and_more_than_500(self, value):
        with pytest.raises(ValidationError):
            validate(FurtherInformation, value)

    @pytest.mark.parametrize("value", ["<script>", "a > b", "bad\x00value"])
    def test_still_rejects_angle_brackets_and_control_characters(self, value):
        with pytest.raises(ValidationError):
            validate(FurtherInformation, value)


class TestRefusalJustification:
    @pytest.mark.parametrize(
        "value", ["Out of scope.", "Line one\nLine two", "A" * 1500]
    )
    def test_accepts_up_to_1500_characters(self, value):
        assert validate(RefusalJustification, value) == value

    @pytest.mark.parametrize("value", ["A" * 1501, "<b>", "bad\x00value"])
    def test_rejects_more_than_1500_angle_brackets_and_control_characters(self, value):
        with pytest.raises(ValidationError):
            validate(RefusalJustification, value)


class TestRejectionReason:
    @pytest.mark.parametrize(
        "value",
        ["A", "Rejected following manual review.", "Line one\nLine two", "A" * 500],
    )
    def test_accepts_one_to_500_characters(self, value):
        assert validate(RejectionReason, value) == value

    @pytest.mark.parametrize(
        "value", ["", " ", "\n\t", "A" * 501, "<b>", "bad\x00value"]
    )
    def test_rejects_blank_more_than_500_angle_brackets_and_control_characters(
        self, value
    ):
        with pytest.raises(ValidationError):
            validate(RejectionReason, value)


class TestSingleLineText:
    @pytest.mark.parametrize(
        "value",
        [
            "740e5834-3a29-46b4-9a6f-16142fde533a",
            "dev-APP-123456",
            "a b",
            "Zoë <b>",
            "",
        ],
    )
    def test_accepts_ordinary_text(self, value):
        assert validate(SingleLineText, value) == value

    @pytest.mark.parametrize(
        "value", ["a\nb", "a\rb", "a\tb", "a\x00b", "a\x1bb", "a\x7fb", "a\u200bb"]
    )
    def test_rejects_newlines_and_control_or_format_characters(self, value):
        with pytest.raises(ValidationError):
            validate(SingleLineText, value)

    @pytest.mark.parametrize("value", [None, 123])
    def test_rejects_non_string_input(self, value):
        with pytest.raises(ValidationError):
            validate(SingleLineText, value)


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
