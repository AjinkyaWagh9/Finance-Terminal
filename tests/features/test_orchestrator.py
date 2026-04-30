# tests/features/test_orchestrator.py
from datetime import date, datetime
import json, uuid
from finterminal.data.duckdb_store import connect
from finterminal.market_data.store import upsert_prices_eod
from finterminal.outcomes.schema import SignalType
from finterminal.features.registry import COMPUTABLE_NAMES, PLACEHOLDER_NAMES, V1_FEATURES
from finterminal.features.orchestrator import compute_for_signal

def _seed_full(conn):
    # Equity ticker history
    rows = [{"trade_date": date.fromordinal(date(2026,1,1).toordinal()+i),
             "ticker":"TCS","open":0.0,"high":0.0,"low":0.0,
             "close":100.0+i,"volume":0} for i in range(120)]
    upsert_prices_eod(conn, rows, source="test")
    # Nifty history
    rows = [{"trade_date": date.fromordinal(date(2025,1,1).toordinal()+i),
             "ticker":"_NIFTY50","open":0.0,"high":0.0,"low":0.0,
             "close":20000.0+i*2,"volume":0} for i in range(485)]
    upsert_prices_eod(conn, rows, source="test")

def test_compute_for_signal_returns_18_keys(tmp_path):
    conn = connect(str(tmp_path / "t.duckdb"))
    _seed_full(conn)
    sig_id = str(uuid.uuid4())
    out = compute_for_signal(
        conn, signal_id=sig_id,
        signal_type=SignalType.CLUSTER_MOMENTUM, ticker="TCS",
        ts_emitted=datetime(2026, 4, 20, 10, 0),
        payload={"story_count_delta": 3.0, "cluster_id": "c1"},
    )
    assert set(out.keys()) == {f.name for f in V1_FEATURES}
    # Placeholders are all is_missing
    for name in PLACEHOLDER_NAMES:
        assert out[name]["is_missing"] is True and out[name]["value"] is None

def test_compute_for_signal_marks_cluster_z_missing_for_other_signal_types(tmp_path):
    conn = connect(str(tmp_path / "t.duckdb"))
    _seed_full(conn)
    out = compute_for_signal(
        conn, signal_id=str(uuid.uuid4()),
        signal_type=SignalType.SENTIMENT_DELTA, ticker="TCS",
        ts_emitted=datetime(2026, 4, 20, 10, 0), payload={},
    )
    assert out["cluster_momentum_z"]["is_missing"] is True
    assert out["narrative_price_divergence"]["is_missing"] is True
