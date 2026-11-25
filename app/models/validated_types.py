import unicodedata
from typing import Annotated

from pydantic import AfterValidator, BeforeValidator, StringConstraints

MAX_SHORT_TEXT_LENGTH = 50
MAX_NAME_LENGTH = 100
MAX_RELATIONSHIP_LENGTH = 70
_ALLOWED_PROSE_WHITESPACE = frozenset("\n\r\t")
_FORBIDDEN_PROSE_CHARACTERS = frozenset("<>")
_CONTROL_CATEGORIES = frozenset({"Cc", "Cf"})
_CURLY_APOSTROPHES = str.maketrans({"\u2018": "'", "\u2019": "'"})

# A letter with any combining marks. Marks are only valid after a letter, so a bare
# combining mark is rejected, while letters with no single-character form still pass.
_LETTER = r"\p{L}\p{M}*"
_NAME_PATTERN = rf"^{_LETTER}(?:{_LETTER}|[ '-])*$"
_NAME_OR_EMPTY_PATTERN = rf"^(?:{_LETTER}(?:{_LETTER}|[ '-])*)?$"


def _normalise_short_text(value: object) -> object:
    """Trim, fold curly apostrophes and compose accents before the checks run.

    Composing (NFC) matters because an accent typed as a separate mark is a different
    string to the single-character form, and would otherwise fail the letter check.
    Non-strings are returned unchanged so the type check reports them.
    """
    if not isinstance(value, str):
        return value
    return unicodedata.normalize("NFC", value.translate(_CURLY_APOSTROPHES)).strip()


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

AddressText = Annotated[
    str,
    StringConstraints(
        max_length=MAX_SHORT_TEXT_LENGTH, pattern=r"^[A-Za-z0-9][A-Za-z0-9' ,./-]*$"
    ),
]

# The UI sends "" when there is no coroner's reference, and duplicate detection
# treats "" as "not provided".
CoronersReference = Annotated[
    str,
    StringConstraints(
        max_length=MAX_SHORT_TEXT_LENGTH, pattern=r"^([A-Za-z0-9][A-Za-z0-9 ./-]*)?$"
    ),
    BeforeValidator(_normalise_short_text),
]
