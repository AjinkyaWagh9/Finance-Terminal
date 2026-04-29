from __future__ import annotations
from datetime import date

# NSE official trading holidays for 2026 (verify annually).
# Source: https://www.nseindia.com/resources/exchange-communication-holidays
_HOLIDAYS_2026: frozenset[date] = frozenset({
    date(2026, 1, 26),  # Republic Day
    date(2026, 3, 6),   # Holi
    date(2026, 3, 19),  # Eid-ul-Fitr (tentative)
    date(2026, 4, 3),   # Good Friday
    date(2026, 4, 14),  # Dr. Ambedkar Jayanti
    date(2026, 5, 1),   # Maharashtra Day
    date(2026, 5, 27),  # Eid-ul-Adha (tentative)
    date(2026, 8, 15),  # Independence Day
    date(2026, 8, 27),  # Ganesh Chaturthi (tentative)
    date(2026, 10, 2),  # Mahatma Gandhi Jayanti
    date(2026, 11, 20), # Diwali (Laxmi Pujan, tentative)
    date(2026, 12, 25), # Christmas
})

def is_holiday(d: date) -> bool:
    return d in _HOLIDAYS_2026

def is_trading_day(d: date) -> bool:
    return d.weekday() < 5 and not is_holiday(d)
