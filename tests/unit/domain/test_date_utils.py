from datetime import date

from app.domain.date_utils import add_calendar_months


def test_add_calendar_months_simple():
    assert add_calendar_months(date(2026, 5, 1), 3) == date(2026, 8, 1)


def test_add_calendar_months_crosses_year_boundary():
    assert add_calendar_months(date(2025, 11, 15), 3) == date(2026, 2, 15)


def test_add_calendar_months_clamps_to_shorter_month():
    # 30 Nov + 3 months -> Feb has no 30th, clamp to 28th (non-leap year)
    assert add_calendar_months(date(2025, 11, 30), 3) == date(2026, 2, 28)


def test_add_calendar_months_clamps_to_leap_february():
    assert add_calendar_months(date(2023, 11, 29), 3) == date(2024, 2, 29)


def test_add_calendar_months_zero_months_returns_same_date():
    assert add_calendar_months(date(2026, 5, 10), 0) == date(2026, 5, 10)
