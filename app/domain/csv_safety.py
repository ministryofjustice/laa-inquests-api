import unicodedata

_FORMULA_TRIGGERS = frozenset("=+-@＝＋－＠\t\r")
_CONTROL_CATEGORIES = frozenset({"Cc", "Cf"})


def _is_control(char: str) -> bool:
    return unicodedata.category(char) in _CONTROL_CATEGORIES


def starts_with_formula_trigger(value: str) -> bool:
    """Whether a spreadsheet could read the value as a formula.

    Leading whitespace and control/format characters are skipped, as spreadsheet
    applications ignore them before the formula prefix.
    """
    if not value:
        return False
    if value[0] in _FORMULA_TRIGGERS or _is_control(value[0]):
        return True
    for char in value:
        if char.isspace() or _is_control(char):
            continue
        return char in _FORMULA_TRIGGERS
    return False


def neutralise_csv_formula(value: str) -> str:
    """Stop spreadsheet applications from evaluating free text as a formula."""
    return f"'{value}" if starts_with_formula_trigger(value) else value
