import csv
import unicodedata
from collections.abc import Iterable, Sequence
from typing import TextIO

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


class Amount(str):
    """A money amount formatted by our own code, never text a user typed.

    The only string the writer leaves alone, because a negative amount such as
    "-100.00" starts with a formula trigger but cannot be evaluated. String
    operations on it return a plain str, which is neutralised again, so losing the
    type fails safe.
    """

    __slots__ = ()


class SafeCsvWriter:
    """CSV writer that neutralises every string cell, in every column.

    Safe by default: nothing about a column or a value's content exempts it, so a
    newly added report column cannot reach a spreadsheet unprotected. Only `Amount`
    cells and non-string values (numbers, dates, None) are written as they are.
    Quoting is left to `csv.writer`.
    """

    def __init__(self, buffer: TextIO, headers: Sequence[str]) -> None:
        self._column_count = len(headers)
        self._writer = csv.writer(buffer)
        self._writer.writerow(headers)

    def writerow(self, row: Sequence[object]) -> None:
        if len(row) != self._column_count:
            raise ValueError(
                f"Row has {len(row)} cells but the report has {self._column_count} columns"
            )
        self._writer.writerow([_safe_cell(cell) for cell in row])

    def writerows(self, rows: Iterable[Sequence[object]]) -> None:
        for row in rows:
            self.writerow(row)


def _safe_cell(cell: object) -> object:
    if isinstance(cell, str) and not isinstance(cell, Amount):
        return neutralise_csv_formula(cell)
    return cell
