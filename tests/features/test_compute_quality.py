from datetime import date, datetime
import pytest
from finterminal.data.duckdb_store import connect, upsert_fundamentals
from finterminal.features.compute_quality import (
    compute_roe, compute_leverage, compute_earnings_growth,
)

def _seed(conn, ticker, as_of, roe=0.18, d2e=0.5, ni=1000.0):
    upsert_fundamentals(conn, {
        "ticker": ticker, "as_of": as_of,
        "roe": roe, "debt_to_equity": d2e, "net_income_ttm": ni,
    })

TS = datetime(2026, 4, 30, 10, 0)

# ---------- roe ----------

def test_compute_roe_returns_value(tmp_path):
    conn = connect(str(tmp_path / "t.duckdb"))
    _seed(conn, "TCS", date(2026, 1, 1), roe=0.18)
    v, m = compute_roe(conn, ticker="TCS", ts_emitted=TS)
    assert m is False
    assert abs(v - 0.18) < 1e-9

def test_compute_roe_missing_when_no_data(tmp_path):
    conn = connect(str(tmp_path / "t.duckdb"))
    v, m = compute_roe(conn, ticker="TCS", ts_emitted=TS)
    assert v is None and m is True

def test_compute_roe_missing_when_stale(tmp_path):
    conn = connect(str(tmp_path / "t.duckdb"))
    _seed(conn, "TCS", date(2025, 12, 1), roe=0.18)   # > 120 days stale
    v, m = compute_roe(conn, ticker="TCS", ts_emitted=TS)
    assert v is None and m is True

def test_compute_roe_uses_latest_row(tmp_path):
    conn = connect(str(tmp_path / "t.duckdb"))
    _seed(conn, "TCS", date(2026, 1, 1), roe=0.10)
    _seed(conn, "TCS", date(2026, 3, 1), roe=0.20)
    v, m = compute_roe(conn, ticker="TCS", ts_emitted=TS)
    assert m is False and abs(v - 0.20) < 1e-9

# ---------- leverage ----------

def test_compute_leverage_returns_value(tmp_path):
    conn = connect(str(tmp_path / "t.duckdb"))
    _seed(conn, "TCS", date(2026, 1, 1), d2e=1.5)
    v, m = compute_leverage(conn, ticker="TCS", ts_emitted=TS)
    assert m is False and abs(v - 1.5) < 1e-9

def test_compute_leverage_missing_when_no_data(tmp_path):
    conn = connect(str(tmp_path / "t.duckdb"))
    v, m = compute_leverage(conn, ticker="TCS", ts_emitted=TS)
    assert v is None and m is True

# ---------- earnings_growth ----------

def test_compute_earnings_growth_yoy(tmp_path):
    conn = connect(str(tmp_path / "t.duckdb"))
    _seed(conn, "TCS", date(2026, 1, 1), ni=1200.0)   # latest
    _seed(conn, "TCS", date(2025, 10, 1), ni=1000.0)  # prior
    v, m = compute_earnings_growth(conn, ticker="TCS", ts_emitted=TS)
    assert m is False
    assert abs(v - 0.20) < 1e-9   # (1200 - 1000) / 1000 = 0.20

def test_compute_earnings_growth_missing_when_only_one_row(tmp_path):
    conn = connect(str(tmp_path / "t.duckdb"))
    _seed(conn, "TCS", date(2026, 1, 1), ni=1000.0)
    v, m = compute_earnings_growth(conn, ticker="TCS", ts_emitted=TS)
    assert v is None and m is True

def test_compute_earnings_growth_missing_when_prior_is_zero(tmp_path):
    conn = connect(str(tmp_path / "t.duckdb"))
    _seed(conn, "TCS", date(2026, 1, 1), ni=500.0)
    _seed(conn, "TCS", date(2025, 10, 1), ni=0.0)
    v, m = compute_earnings_growth(conn, ticker="TCS", ts_emitted=TS)
    assert v is None and m is True

def test_compute_earnings_growth_negative_growth(tmp_path):
    conn = connect(str(tmp_path / "t.duckdb"))
    _seed(conn, "TCS", date(2026, 1, 1), ni=800.0)
    _seed(conn, "TCS", date(2025, 10, 1), ni=1000.0)
    v, m = compute_earnings_growth(conn, ticker="TCS", ts_emitted=TS)
    assert m is False
    assert abs(v - (-0.20)) < 1e-9
