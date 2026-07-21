import calendar
from datetime import date


def add_calendar_months(start: date, months: int) -> date:
    """Add whole calendar months, clamping the day to the target month length."""
    month_index = start.month - 1 + months
    year = start.year + month_index // 12
    month = month_index % 12 + 1
    day = min(start.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)
