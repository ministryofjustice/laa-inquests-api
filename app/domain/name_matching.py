import unicodedata

# Letters that do not decompose into a base letter and a mark, so dropping marks alone
# would leave them different. Applied after case folding, so lower case only.
_LETTER_FORMS = {
    "ł": "l",
    "ø": "o",
    "đ": "d",
    "ð": "d",
    "ħ": "h",
    "ı": "i",
    "æ": "ae",
    "œ": "oe",
    "þ": "th",
}

# Apostrophes are ignored, and hyphens count as a space, so "O'Brien" matches "OBrien"
# and "Mary-Jane" matches "Mary Jane".
_APOSTROPHES = "'\u2018\u2019\u02bc`\u00b4"
_HYPHENS = "-\u2010\u2011\u2012\u2013"

_TRANSLATION = str.maketrans(
    {ord(char): replacement for char, replacement in _LETTER_FORMS.items()}
    | {ord(char): None for char in _APOSTROPHES}
    | {ord(char): " " for char in _HYPHENS}
)


def name_match_key(value: str) -> str:
    """A key for comparing names that ignores case, accents and punctuation variants.

    Two names with the same key are treated as the same name when looking for duplicate
    applications. The stored name is never changed. Case folding comes first so that
    letters like "ß" and "İ" are handled, and marks are dropped after decomposing so
    "é" typed as one character or as "e" plus an accent gives the same key.
    """
    folded = value.casefold().translate(_TRANSLATION)
    decomposed = unicodedata.normalize("NFKD", folded)
    without_marks = "".join(
        char for char in decomposed if not unicodedata.combining(char)
    )
    return " ".join(without_marks.split())
