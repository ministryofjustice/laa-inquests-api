from datetime import UTC, date, datetime

import pytest

from app.use_cases.exceptions import InvalidDateRangeError
from app.use_cases.report_date_range import resolve_report_window


def test_resolve_report_window_returns_utc_midnight_start_and_next_day_exclusive_end():
    window_start, window_end = resolve_report_window(
        date(2025, 3, 15), date(2025, 3, 15), max_days=90
    )

    assert window_start == datetime(2025, 3, 15, 0, 0, tzinfo=UTC)
    assert window_end == datetime(2025, 3, 16, 0, 0, tzinfo=UTC)


def test_resolve_report_window_rejects_from_date_after_to_date():
    with pytest.raises(InvalidDateRangeError) as exc_info:
        resolve_report_window(date(2025, 3, 16), date(2025, 3, 15), max_days=90)

    assert str(exc_info.value) == "The 'from' date must be on or before the 'to' date."


def test_resolve_report_window_rejects_range_longer_than_max_days():
    with pytest.raises(InvalidDateRangeError) as exc_info:
        resolve_report_window(date(2025, 1, 1), date(2025, 4, 1), max_days=90)

    assert str(exc_info.value) == "The date range must not exceed 90 days."


def test_resolve_report_window_accepts_range_of_exactly_max_days():
    window_start, window_end = resolve_report_window(
        date(2025, 1, 1), date(2025, 3, 31), max_days=90
    )

    assert window_start == datetime(2025, 1, 1, tzinfo=UTC)
    assert window_end == datetime(2025, 4, 1, tzinfo=UTC)
