"""NSE-specific helpers (ticker normalization, RSS feeds, corporate filings).

Phase 1: just the suffix helper. Phase 2.5 grows this significantly.
"""

from __future__ import annotations


def normalize_ticker(symbol: str, exchange: str = "NSE") -> str:
    """Maps a bare symbol like 'RELIANCE' to OpenBB-friendly 'RELIANCE.NS'.

    Idempotent: 'RELIANCE.NS' returns 'RELIANCE.NS' unchanged.
    """
    symbol = symbol.upper().strip()
    if "." in symbol:
        return symbol
    suffix = ".NS" if exchange.upper() == "NSE" else ".BO"
    return f"{symbol}{suffix}"
