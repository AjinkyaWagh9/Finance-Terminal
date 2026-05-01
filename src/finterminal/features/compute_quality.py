from __future__ import annotations
from datetime import datetime
import duckdb

from .freshness import is_fundamentals_data_fresh

Result = tuple[float | None, bool]   # (value, is_missing)

MIN_CROSS_SECTION_COUNT = 3   # minimum tickers needed for quality_score z-scoring


def compute_roe(conn: duckdb.DuckDBPyConnection, *,
                ticker: str, ts_emitted: datetime, **_) -> Result:
    if not is_fundamentals_data_fresh(conn, ticker, ts_emitted=ts_emitted):
        return None, True
    row = conn.execute(
        "SELECT roe FROM fundamentals "
        "WHERE ticker = ? AND as_of <= ? ORDER BY as_of DESC LIMIT 1",
        [ticker, ts_emitted.date()],
    ).fetchone()
    if row is None or row[0] is None:
        return None, True
    return row[0], False


def compute_leverage(conn: duckdb.DuckDBPyConnection, *,
                     ticker: str, ts_emitted: datetime, **_) -> Result:
    if not is_fundamentals_data_fresh(conn, ticker, ts_emitted=ts_emitted):
        return None, True
    row = conn.execute(
        "SELECT debt_to_equity FROM fundamentals "
        "WHERE ticker = ? AND as_of <= ? ORDER BY as_of DESC LIMIT 1",
        [ticker, ts_emitted.date()],
    ).fetchone()
    if row is None or row[0] is None:
        return None, True
    return row[0], False


def compute_earnings_growth(conn: duckdb.DuckDBPyConnection, *,
                            ticker: str, ts_emitted: datetime, **_) -> Result:
    if not is_fundamentals_data_fresh(conn, ticker, ts_emitted=ts_emitted):
        return None, True
    rows = conn.execute(
        "SELECT as_of, net_income_ttm FROM fundamentals "
        "WHERE ticker = ? AND as_of <= ? ORDER BY as_of DESC LIMIT 2",
        [ticker, ts_emitted.date()],
    ).fetchall()
    if len(rows) < 2:
        return None, True
    curr, prev = rows[0][1], rows[1][1]
    if curr is None or prev is None or prev == 0:
        return None, True
    return (curr - prev) / abs(prev), False
