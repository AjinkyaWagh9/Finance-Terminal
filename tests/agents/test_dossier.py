"""Source-dossier shape tests."""
from __future__ import annotations

from finterminal.agents._dossier import build_source_dossier


_QUOTE = {
    "ticker": "RELIANCE.NS",
    "last_price": 2945.50,
    "change_pct": 1.2,
    "as_of": "2026-04-28T15:30:00+05:30",
    "provider": "yfinance",
}
_FUND = {
    "pe_ttm": 23.4,
    "roe": 0.091,
    "debt_to_equity": 0.45,
}
_NEWS = [
    {"source": "Moneycontrol", "headline": "Reliance Q4 net profit up 8%; refining margins improve",
     "published_at": "2026-04-26"},
    {"source": "Livemint", "headline": "Jio user adds slow to 3.4M in Q4",
     "published_at": "2026-04-25"},
]


def test_dossier_includes_quote_tag():
    out = build_source_dossier("RELIANCE.NS", _QUOTE, _FUND, _NEWS)
    assert "[QUOTE]" in out
    assert "RELIANCE.NS" in out
    assert "2945" in out  # price digits present


def test_dossier_includes_fundamental_tags():
    out = build_source_dossier("RELIANCE.NS", _QUOTE, _FUND, _NEWS)
    assert "[FUND-PE]" in out and "23.4" in out
    assert "[FUND-ROE]" in out
    assert "[FUND-DEBT]" in out  # debt_to_equity rendered as [FUND-DEBT]


def test_dossier_news_uses_indexed_tags():
    out = build_source_dossier("RELIANCE.NS", _QUOTE, _FUND, _NEWS)
    assert "[NEWS-1]" in out
    assert "[NEWS-2]" in out
    assert "Moneycontrol" in out
    assert "Livemint" in out


def test_dossier_handles_missing_fundamentals():
    out = build_source_dossier("RELIANCE.NS", _QUOTE, None, _NEWS)
    assert "[QUOTE]" in out
    # Fundamentals section absent or marked unavailable; must not crash:
    assert "[FUND-PE]" not in out
    assert "fundamentals unavailable" in out.lower()


def test_dossier_handles_no_news():
    out = build_source_dossier("RELIANCE.NS", _QUOTE, _FUND, [])
    assert "[NEWS-1]" not in out
    assert "no news" in out.lower()


def test_dossier_ends_with_verify_directive():
    out = build_source_dossier("RELIANCE.NS", _QUOTE, _FUND, _NEWS)
    assert "VERIFY" in out
