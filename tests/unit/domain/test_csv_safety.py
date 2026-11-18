import pytest

from app.domain.csv_safety import neutralise_csv_formula, starts_with_formula_trigger

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
