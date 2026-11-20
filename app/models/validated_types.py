import unicodedata
from typing import Annotated

from pydantic import AfterValidator, StringConstraints

MAX_SHORT_TEXT_LENGTH = 50
_ALLOWED_PROSE_WHITESPACE = frozenset("\n\r\t")
_FORBIDDEN_PROSE_CHARACTERS = frozenset("<>")
_CONTROL_CATEGORIES = frozenset({"Cc", "Cf"})


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
    StringConstraints(
        max_length=MAX_SHORT_TEXT_LENGTH, pattern=r"^[A-Za-z][A-Za-z' -]*$"
    ),
]

AddressText = Annotated[
    str,
    StringConstraints(
        max_length=MAX_SHORT_TEXT_LENGTH, pattern=r"^[A-Za-z0-9][A-Za-z0-9' ,./-]*$"
    ),
]

CoronersReference = Annotated[
    str,
    StringConstraints(
        max_length=MAX_SHORT_TEXT_LENGTH, pattern=r"^[A-Za-z0-9][A-Za-z0-9 ./-]*$"
    ),
]
