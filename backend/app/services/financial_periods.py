"""Calendar ownership and the narrow month-close cash execution exception."""

from calendar import monthrange
from datetime import date


def next_month(month: str) -> str:
    year, number = map(int, month.split("-"))
    return f"{year + (number == 12):04d}-{1 if number == 12 else number + 1:02d}"


def is_month_end(day: date) -> bool:
    return day.day == monthrange(day.year, day.month)[1]


def fixed_execution_month(day: date, last_closed_month: str | None) -> str:
    """Keep the actual date; only a closed month-end opens its next cash period."""
    month = day.strftime("%Y-%m")
    if last_closed_month and month <= last_closed_month:
        if month == last_closed_month and is_month_end(day):
            return next_month(month)
        raise ValueError("이미 마감한 달의 현금성 고정지출은 확인할 수 없습니다.")
    return month


def valid_fixed_confirmation_period(
    day: date, confirmed_month: str | None, last_closed_month: str | None,
) -> bool:
    actual_month = day.strftime("%Y-%m")
    return confirmed_month == actual_month or (
        is_month_end(day)
        and last_closed_month == actual_month
        and confirmed_month == next_month(actual_month)
    )
