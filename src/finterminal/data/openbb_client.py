"""Thin wrapper around OpenBB SDK. Defensive — providers vary in field names.

Phase 1 uses yfinance (free, no PAT required). Phase 3 will add Finnhub
for US fundamentals via env-var-keyed config.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

# Providers to try in order. yfinance covers Indian + US for free.
_QUOTE_PROVIDERS = ["yfinance"]
_FUNDAMENTAL_PROVIDERS = ["yfinance"]
_NEWS_PROVIDERS = ["yfinance"]


def _to_dict(obj: Any) -> dict:
    """OpenBB v4 returns Pydantic models; normalize to dict."""
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if isinstance(obj, dict):
        return obj
    return dict(obj)


def _first_present(d: dict, *keys: str, default=None):
    for k in keys:
        if k in d and d[k] is not None:
            return d[k]
    return default


def fetch_quote(ticker: str) -> dict:
    """Returns latest quote: ticker, as_of, last_price, change_pct, volume, market_cap, raw."""
    from openbb import obb  # imported lazily — OpenBB has slow cold start

    last_err: Exception | None = None
    for provider in _QUOTE_PROVIDERS:
        try:
            resp = obb.equity.price.quote(ticker, provider=provider)
            results = resp.results or []
            if results:
                d = _to_dict(results[0])
                return {
                    "ticker": ticker,
                    "as_of": datetime.now(timezone.utc),
                    "last_price": _first_present(d, "last_price", "price", "close", "regular_market_price"),
                    "change_pct": _first_present(d, "change_percent", "regular_market_change_percent"),
                    "volume": _first_present(d, "volume", "regular_market_volume"),
                    "market_cap": _first_present(d, "market_cap"),
                    "provider": provider,
                    "raw": d,
                }
            last_err = ValueError(f"empty quote from {provider}")
        except Exception as exc:  # noqa: BLE001 — log and try next provider/fallback
            last_err = exc
            logger.warning("quote fetch via %s failed for %s: %s", provider, ticker, exc)
            continue

        # Yahoo's quote endpoint is intermittently flaky for Indian tickers (cookie/crumb auth).
        # Historical bars endpoint is more reliable — synthesize a quote from the last two closes.
        try:
            hist = obb.equity.price.historical(ticker, provider=provider)
            rows = hist.results or []
            if rows:
                last = _to_dict(rows[-1])
                prev = _to_dict(rows[-2]) if len(rows) >= 2 else None
                last_close = last.get("close")
                prev_close = prev.get("close") if prev else None
                change_pct = (
                    (last_close - prev_close) / prev_close * 100
                    if last_close is not None and prev_close
                    else None
                )
                return {
                    "ticker": ticker,
                    "as_of": datetime.now(timezone.utc),
                    "last_price": last_close,
                    "change_pct": change_pct,
                    "volume": last.get("volume"),
                    "market_cap": None,
                    "provider": f"{provider}/historical",
                    "raw": last,
                }
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            logger.warning("historical fallback via %s failed for %s: %s", provider, ticker, exc)
    raise RuntimeError(f"All providers failed for {ticker}: {last_err!r}")


def fetch_fundamentals(ticker: str) -> dict:
    """Returns key ratios. Field availability varies by provider."""
    from openbb import obb

    last_err: Exception | None = None
    for provider in _FUNDAMENTAL_PROVIDERS:
        try:
            resp = obb.equity.fundamental.metrics(ticker, provider=provider)
            results = resp.results or []
            if not results:
                last_err = ValueError(f"empty fundamentals from {provider}")
                continue
            d = _to_dict(results[0])
            return {
                "ticker": ticker,
                "as_of": datetime.now(timezone.utc).date(),
                "pe_ttm": _first_present(d, "pe_ratio", "trailing_pe", "price_to_earnings"),
                "eps_ttm": _first_present(d, "eps", "trailing_eps"),
                "roe": _first_present(d, "return_on_equity", "roe"),
                "roce": _first_present(d, "return_on_capital_employed", "roce"),
                "debt_to_equity": _first_present(d, "debt_to_equity"),
                "revenue_ttm": _first_present(d, "revenue", "trailing_revenue"),
                "net_income_ttm": _first_present(d, "net_income"),
                "provider": provider,
                "raw": d,
            }
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            logger.warning("fundamentals fetch via %s failed for %s: %s", provider, ticker, exc)
    raise RuntimeError(f"All providers failed for {ticker}: {last_err!r}")


def fetch_news(ticker: str, limit: int = 20) -> list[dict]:
    """Returns recent news items normalized to our schema."""
    from openbb import obb

    last_err: Exception | None = None
    for provider in _NEWS_PROVIDERS:
        try:
            resp = obb.news.company(symbol=ticker, limit=limit, provider=provider)
            results = resp.results or []
            items = []
            for n in results:
                d = _to_dict(n)
                items.append({
                    "id": _first_present(d, "id", "url", "title"),
                    "ticker": ticker,
                    "source": _first_present(d, "source", "publisher"),
                    "headline": _first_present(d, "title", "headline"),
                    "url": _first_present(d, "url"),
                    "published_at": _first_present(d, "date", "published", "published_at"),
                    "body": _first_present(d, "text", "summary", "body"),
                })
            return items
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            logger.warning("news fetch via %s failed for %s: %s", provider, ticker, exc)
    raise RuntimeError(f"All providers failed for {ticker}: {last_err!r}")
