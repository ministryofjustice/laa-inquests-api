import pytest

from app.models.application.enums import ReasonForRefusal


@pytest.mark.parametrize(
    ("reason", "expected_history_label"),
    [
        (ReasonForRefusal.NOT_IN_SCOPE, "Not in scope"),
        (ReasonForRefusal.INSUFFICIENT_INFORMATION, "Insufficient information"),
        (ReasonForRefusal.DUPLICATE_CASE, "Duplicate case"),
    ],
)
def test_history_label_returns_human_readable_string(
    reason: ReasonForRefusal, expected_history_label: str
) -> None:
    assert reason.history_label == expected_history_label
