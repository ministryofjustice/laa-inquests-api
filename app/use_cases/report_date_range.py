from datetime import UTC, date, datetime, time, timedelta

from app.use_cases.exceptions import InvalidDateRangeError


def resolve_report_window(
    from_date: date, to_date: date, max_days: int
) -> tuple[datetime, datetime]:
    """Return the UTC [start, end) window covering the inclusive date range."""
    if from_date > to_date:
        raise InvalidDateRangeError(
            "The 'from' date must be on or before the 'to' date."
        )
    if (to_date - from_date).days + 1 > max_days:
        raise InvalidDateRangeError(f"The date range must not exceed {max_days} days.")
    return (
        datetime.combine(from_date, time.min, tzinfo=UTC),
        datetime.combine(to_date + timedelta(days=1), time.min, tzinfo=UTC),
    )
