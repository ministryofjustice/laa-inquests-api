import re
import unicodedata
from typing import Annotated

from pydantic import AfterValidator, BeforeValidator, StringConstraints

MAX_SHORT_TEXT_LENGTH = 50
MAX_NAME_LENGTH = 100
MAX_RELATIONSHIP_LENGTH = 70
MAX_ADDRESS_LENGTH = 100
MAX_COUNTY_LENGTH = 50
MAX_ORGANISATION_LENGTH = 100
MIN_ADDRESS_LINE_LENGTH = 2
MIN_TOWN_LENGTH = 2
MIN_COUNTY_LENGTH = 3
MAX_PREVIOUS_REFERENCE_LENGTH = 35
MAX_NINO_LENGTH = 15
MIN_POSTCODE_LENGTH = 5
MAX_POSTCODE_LENGTH = 8
MAX_OFFICE_CODE_LENGTH = 20
MAX_EMAIL_LENGTH = 254
MAX_REFERENCE_PARAM_LENGTH = 20
MAX_SEARCH_REFERENCE_LENGTH = 50
_ALLOWED_PROSE_WHITESPACE = frozenset("\n\r\t")
_FORBIDDEN_PROSE_CHARACTERS = frozenset("<>")
_CONTROL_CATEGORIES = frozenset({"Cc", "Cf"})
_CURLY_APOSTROPHES = str.maketrans({"\u2018": "'", "\u2019": "'"})

# A letter with any combining marks. Marks are only valid after a letter, so a bare
# combining mark is rejected, while letters with no single-character form still pass.
_LETTER = r"\p{L}\p{M}*"
_NAME_PATTERN = rf"^{_LETTER}(?:{_LETTER}|[ '-])*$"
_NAME_OR_EMPTY_PATTERN = rf"^(?:{_LETTER}(?:{_LETTER}|[ '-])*)?$"

# These mirror the external UI. Address text is ASCII only there, and a value must
# contain a letter or digit (a letter for place names) so "--" or "&&" is not accepted.
_ADDRESS_LINE_PATTERN = r"^[ '.,/&-]*[A-Za-z0-9][A-Za-z0-9 '.,/&-]*$"
_PLACE_NAME_PATTERN = r"^[ '-]*[A-Za-z][A-Za-z '-]*$"

# Recipient and organisation names mirror the UI: Unicode letters and digits, with a
# little punctuation for names like "Smith & Co., Ltd". At least one letter or digit.
_ALPHANUMERIC = rf"(?:{_LETTER}|\p{{N}})"
_ORGANISATION_BODY = rf"[ '.,&-]*{_ALPHANUMERIC}(?:{_ALPHANUMERIC}|[ '.,&-])*"
_RECIPIENT_NAME_PATTERN = rf"^{_ORGANISATION_BODY}$"
_ORGANISATION_NAME_PATTERN = rf"^(?:{_ORGANISATION_BODY})?$"

_REFERENCE_TEXT_PATTERN = r"^(?:[A-Za-z0-9][A-Za-z0-9 ./-]*)?$"
_POSTCODE_PATTERN = r"^[A-Za-z0-9 ]+$"
_OFFICE_CODE_PATTERN = r"^[A-Za-z0-9]+$"
_REFERENCE_PARAM_PATTERN = r"^[A-Za-z0-9-]+$"
_FIRM_CODE_PATTERN = r"^[A-Za-z0-9]+$"

# Letters, digits and ._%+'#- before the @ (a quote mark is common in surnames, and "#"
# appears in guest-account usernames such as "jane_firm.com#EXT#@tenant..."), and ASCII
# domain labels. Nothing that could break out of a header, HTML or a CSV cell.
_EMAIL_PATTERN = (
    r"^[A-Za-z0-9._%+'#-]{1,64}@"
    r"(?:[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?\.)+[A-Za-z]{2,}$"
)

# The UI's NINO rule, anchored at both ends (the UI's has no end anchor, so anything
# after the suffix letter passes there). Python's re is used because the prefix
# exclusions need a lookahead, which the regex engine behind `pattern` does not have.
# ASCII mode stops "ſ" and the Kelvin sign matching "s" and "k" case-insensitively.
_NINO_PATTERN = re.compile(
    r"(?!BG|GB|NK|KN|TN|NT|ZZ)[A-CEG-HJ-TW-Z]{2} *[0-9]{6} *[A-D]",
    re.ASCII | re.IGNORECASE,
)


def _normalise_short_text(value: object) -> object:
    """Trim, fold curly apostrophes and compose accents before the checks run.

    Composing (NFC) matters because an accent typed as a separate mark is a different
    string to the single-character form, and would otherwise fail the letter check.
    Non-strings are returned unchanged so the type check reports them.
    """
    if not isinstance(value, str):
        return value
    return unicodedata.normalize("NFC", value.translate(_CURLY_APOSTROPHES)).strip()


def _validate_nino(value: str) -> str:
    if not _NINO_PATTERN.fullmatch(value):
        raise ValueError("must be a valid National Insurance number")
    return value


def _validate_prose_text(value: str) -> str:
    for char in value:
        if char in _FORBIDDEN_PROSE_CHARACTERS:
            raise ValueError("must not contain < or >")
        if (
            unicodedata.category(char) in _CONTROL_CATEGORIES
            and char not in _ALLOWED_PROSE_WHITESPACE
        ):
            raise ValueError("must not contain control characters")
    return value


ProseText = Annotated[str, AfterValidator(_validate_prose_text)]

PersonName = Annotated[
    str,
    StringConstraints(max_length=MAX_NAME_LENGTH, pattern=_NAME_PATTERN),
    BeforeValidator(_normalise_short_text),
]

# The UI sends "" when the user says there is no relationship to record.
RelationshipText = Annotated[
    str,
    StringConstraints(
        max_length=MAX_RELATIONSHIP_LENGTH, pattern=_NAME_OR_EMPTY_PATTERN
    ),
    BeforeValidator(_normalise_short_text),
]

AddressLine = Annotated[
    str,
    StringConstraints(
        min_length=MIN_ADDRESS_LINE_LENGTH,
        max_length=MAX_ADDRESS_LENGTH,
        pattern=_ADDRESS_LINE_PATTERN,
    ),
    BeforeValidator(_normalise_short_text),
]

TownName = Annotated[
    str,
    StringConstraints(
        min_length=MIN_TOWN_LENGTH,
        max_length=MAX_ADDRESS_LENGTH,
        pattern=_PLACE_NAME_PATTERN,
    ),
    BeforeValidator(_normalise_short_text),
]

CountyName = Annotated[
    str,
    StringConstraints(
        min_length=MIN_COUNTY_LENGTH,
        max_length=MAX_COUNTY_LENGTH,
        pattern=_PLACE_NAME_PATTERN,
    ),
    BeforeValidator(_normalise_short_text),
]

# One rule for PERSON and ORGANISATION recipients, as in the UI.
RecipientName = Annotated[
    str,
    StringConstraints(
        max_length=MAX_ORGANISATION_LENGTH, pattern=_RECIPIENT_NAME_PATTERN
    ),
    BeforeValidator(_normalise_short_text),
]

# For final and nil bills the UI sends "" when the paying party is blank, and the API
# requires the field to be present for those claim types, so "" must stay valid.
OrganisationName = Annotated[
    str,
    StringConstraints(
        max_length=MAX_ORGANISATION_LENGTH, pattern=_ORGANISATION_NAME_PATTERN
    ),
    BeforeValidator(_normalise_short_text),
]

# The UI sends "" when there is no coroner's reference, and duplicate detection
# treats "" as "not provided".
CoronersReference = Annotated[
    str,
    StringConstraints(
        max_length=MAX_SHORT_TEXT_LENGTH, pattern=_REFERENCE_TEXT_PATTERN
    ),
    BeforeValidator(_normalise_short_text),
]

# Applicants may quote older or other-format references, so this is not forced to the
# INQ-XXX-XXX shape. "" means not provided, as the confirmation email treats it.
PreviousReference = Annotated[
    str,
    StringConstraints(
        max_length=MAX_PREVIOUS_REFERENCE_LENGTH, pattern=_REFERENCE_TEXT_PATTERN
    ),
    BeforeValidator(_normalise_short_text),
]

# Stored as typed, like the UI: no uppercasing and spaces between the groups are kept.
Nino = Annotated[
    str,
    StringConstraints(max_length=MAX_NINO_LENGTH),
    BeforeValidator(_normalise_short_text),
    AfterValidator(_validate_nino),
]

# Uppercased only after the ASCII check, so a character such as "ſ" (which uppercases
# to "S") is rejected instead of being silently turned into ASCII.
Postcode = Annotated[
    str,
    StringConstraints(
        min_length=MIN_POSTCODE_LENGTH,
        max_length=MAX_POSTCODE_LENGTH,
        pattern=_POSTCODE_PATTERN,
    ),
    BeforeValidator(_normalise_short_text),
    AfterValidator(str.upper),
]

OfficeCode = Annotated[
    str,
    StringConstraints(
        min_length=1, max_length=MAX_OFFICE_CODE_LENGTH, pattern=_OFFICE_CODE_PATTERN
    ),
    BeforeValidator(_normalise_short_text),
]

# The provider email and claimant id both come from the signed-in user's Entra username
# and are emailed to, so this is a mailbox-shaped address rather than free text. Case is
# kept as given. `email-validator` is only a transitive dependency, so a regex is used.
EmailAddress = Annotated[
    str,
    StringConstraints(max_length=MAX_EMAIL_LENGTH, pattern=_EMAIL_PATTERN),
    BeforeValidator(_normalise_short_text),
]

# Reference path params are shape-checked only, never matched to the exact INQ-XXX-XXX
# format, so an unknown but well-formed reference is still a 404. They are not trimmed
# or case-folded: the use cases look references up exactly as given.
_ReferenceParam = Annotated[
    str,
    StringConstraints(
        min_length=1,
        max_length=MAX_REFERENCE_PARAM_LENGTH,
        pattern=_REFERENCE_PARAM_PATTERN,
    ),
]
LaaReference = _ReferenceParam
ClaimReference = _ReferenceParam

# The firm id is put into a URL for the provider details service, so anything that could
# change that URL (dots, "?", "#", "/", spaces) is rejected.
FirmCode = Annotated[
    str,
    StringConstraints(
        min_length=1, max_length=MAX_REFERENCE_PARAM_LENGTH, pattern=_FIRM_CODE_PATTERN
    ),
]

# Only capped. The external UI sends whatever the user types into case search, and the
# use case trims, uppercases and returns an empty list for no match, which must stay a
# "no results" page rather than become an error.
SearchReference = Annotated[
    str, StringConstraints(max_length=MAX_SEARCH_REFERENCE_LENGTH)
]
