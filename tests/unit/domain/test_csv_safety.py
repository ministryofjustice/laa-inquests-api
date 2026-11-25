import csv
import io
from decimal import Decimal

import pytest

from app.domain.csv_safety import (
    Amount,
    SafeCsvWriter,
    neutralise_csv_formula,
    starts_with_formula_trigger,
)

ASCII_TRIGGERS = ["=", "+", "-", "@", "\t", "\r"]
FULL_WIDTH_TRIGGERS = ["＝", "＋", "－", "＠"]


class TestNeutraliseCsvFormula:
    @pytest.mark.parametrize("trigger", ASCII_TRIGGERS)
    def test_prefixes_ascii_triggers(self, trigger):
        assert neutralise_csv_formula(f"{trigger}cmd") == f"'{trigger}cmd"

    @pytest.mark.parametrize("trigger", FULL_WIDTH_TRIGGERS)
    def test_prefixes_full_width_triggers(self, trigger):
        assert neutralise_csv_formula(f"{trigger}cmd") == f"'{trigger}cmd"

    @pytest.mark.parametrize(
        "prefix", [" ", "   ", "\u00a0", "\u2003", " \t ", "\n", "\x00", "\u200b"]
    )
    @pytest.mark.parametrize("trigger", ["=", "+", "-", "@"])
    def test_prefixes_triggers_hidden_behind_leading_whitespace_or_control_chars(
        self, prefix, trigger
    ):
        value = f'{prefix}{trigger}HYPERLINK("x")'

        assert neutralise_csv_formula(value) == f"'{value}"

    @pytest.mark.parametrize("control", ["\n", "\x00", "\x1f", "\u200b"])
    def test_prefixes_values_starting_with_a_control_character(self, control):
        assert neutralise_csv_formula(f"{control}text") == f"'{control}text"

    @pytest.mark.parametrize(
        "value",
        [
            "",
            "Jane Smith",
            " Jane",
            "O'Brien",
            "Zoë",
            "a=b",
            "Smith-Jones",
            "jane@example.com",
            "'=already quoted",
            "15-03-2025",
        ],
    )
    def test_leaves_other_values_unchanged(self, value):
        assert neutralise_csv_formula(value) == value

    def test_is_not_applied_twice_to_the_same_dangerous_value(self):
        once = neutralise_csv_formula("=cmd")

        assert neutralise_csv_formula(once) == once


class TestStartsWithFormulaTrigger:
    @pytest.mark.parametrize(
        "value", ["=cmd", " +1", "\n-1", "＝cmd", "\tx", "\u200b@x"]
    )
    def test_true_for_dangerous_values(self, value):
        assert starts_with_formula_trigger(value) is True

    @pytest.mark.parametrize("value", ["", "Jane", " Jane", "a=b", "O'Brien"])
    def test_false_for_safe_values(self, value):
        assert starts_with_formula_trigger(value) is False


def _write(headers, rows):
    buffer = io.StringIO()
    writer = SafeCsvWriter(buffer, headers)
    writer.writerows(rows)
    return list(csv.reader(io.StringIO(buffer.getvalue())))


class TestSafeCsvWriter:
    def test_writes_the_header_row_unchanged(self):
        assert _write(["Name", "Total 0% VAT"], []) == [["Name", "Total 0% VAT"]]

    @pytest.mark.parametrize("trigger", ASCII_TRIGGERS + FULL_WIDTH_TRIGGERS)
    def test_neutralises_text_cells_that_start_with_a_formula_trigger(self, trigger):
        rows = _write(["Name"], [[f"{trigger}cmd"]])

        assert rows[1] == [f"'{trigger}cmd"]

    def test_neutralises_a_joined_name_from_the_ticket_example(self):
        name = '=HYPERLINK("http://www.example.com","Click CsvInjectionTest")'

        rows = _write(["Client Name"], [[name]])

        assert rows[1] == [f"'{name}"]

    @pytest.mark.parametrize("value", [" =cmd", "\u200b@x", "\n+1"])
    def test_neutralises_triggers_hidden_behind_whitespace_or_control_characters(
        self, value
    ):
        assert _write(["Name"], [[value]])[1] == [f"'{value}"]

    def test_leaves_amounts_unchanged_so_negative_values_survive(self):
        rows = _write(["Name", "Invoice Amount"], [["=cmd", Amount("-100.00")]])

        assert rows[1] == ["'=cmd", "-100.00"]

    def test_amount_is_only_exempt_while_it_is_still_an_amount(self):
        derived = f"{Amount('-100.00')}"

        assert _write(["Invoice Amount"], [[derived]])[1] == ["'-100.00"]

    def test_a_plain_string_that_looks_like_an_amount_is_still_neutralised(self):
        assert _write(["Client Name"], [["-100.00"]])[1] == ["'-100.00"]

    def test_passes_non_string_values_through(self):
        rows = _write(["A", "B", "C"], [[1, Decimal("-2.50"), None]])

        assert rows[1] == ["1", "-2.50", ""]

    def test_keeps_multiline_text_and_embedded_quotes_intact(self):
        value = '=Case note added\nShe said "hello", then left'

        assert _write(["Event description"], [[value]])[1] == [f"'{value}"]

    def test_does_not_prefix_an_already_neutralised_cell_again(self):
        assert _write(["Name"], [["'=cmd"]])[1] == ["'=cmd"]

    def test_rejects_rows_that_do_not_match_the_header_width(self):
        with pytest.raises(ValueError, match="2 cells"):
            _write(["A", "B", "C"], [["x", "y"]])
