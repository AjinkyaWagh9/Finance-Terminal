from datetime import date
from finterminal.market_data.calendar import is_holiday, is_trading_day

def test_known_2026_holiday_republic_day():
    assert is_holiday(date(2026, 1, 26)) is True

def test_weekend_is_not_trading_day():
    assert is_trading_day(date(2026, 5, 2)) is False  # Saturday
    assert is_trading_day(date(2026, 5, 3)) is False  # Sunday

def test_regular_weekday_is_trading_day():
    assert is_trading_day(date(2026, 5, 4)) is True   # Monday, not a holiday
