"""Thin wrapper around OpenBB. Day 3 fills in fetch_quote/fetch_fundamentals/fetch_news."""

from __future__ import annotations


def fetch_quote(ticker: str) -> dict:
    """Returns latest quote dict. Day 3 implementation."""
    raise NotImplementedError("Implement on Day 3 using obb.equity.price.quote()")


def fetch_fundamentals(ticker: str) -> dict:
    """Returns key ratios. Day 3 implementation."""
    raise NotImplementedError("Implement on Day 3 using obb.equity.fundamental.metrics()")


def fetch_news(ticker: str, limit: int = 20) -> list[dict]:
    """Returns recent news items. Day 3 implementation."""
    raise NotImplementedError("Implement on Day 3 using obb.news.company()")
