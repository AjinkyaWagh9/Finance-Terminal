# src/finterminal/outcomes/ledger.py
from __future__ import annotations
import json
import uuid
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import duckdb

from finterminal.market_data.macro import snapshot_regime
from .schema import (
    SignalType, SIGNAL_REGISTRY, HORIZONS_DAYS, REGIME_FIELDS,
)

_IST = ZoneInfo("Asia/Kolkata")


def _to_ist_naive(ts: datetime) -> datetime:
    # DuckDB TIMESTAMP is naive; tz-aware values get silently shifted on insert.
    # Normalize to IST wall-clock so date() and the dedup key stay consistent
    # with the stored value.
    if ts.tzinfo is not None:
        ts = ts.astimezone(_IST).replace(tzinfo=None)
    return ts


def emit_signal(conn: duckdb.DuckDBPyConnection, *,
                signal_type: SignalType | str,
                ticker: str,
                ts_emitted: datetime,
                payload: dict[str, Any] | None = None,
                confidence: float | None = None,
                why: str | None = None,
                source_ref: str | None = None) -> str | None:
    """Insert a signal + 5 outcome stubs. Idempotent on (signal_type, ticker, ts_emitted).
    Returns new signal_id, or None if the row was a duplicate."""
    st = SignalType(signal_type) if not isinstance(signal_type, SignalType) else signal_type
    engine = SIGNAL_REGISTRY[st]  # raises KeyError on unknown — surfaced to caller

    ts_emitted = _to_ist_naive(ts_emitted)
    regime = snapshot_regime(conn, as_of=ts_emitted.date())

    signal_id = str(uuid.uuid4())
    cols = ["signal_id", "signal_type", "engine", "ticker", "ts_emitted",
            "payload", "confidence", "why", "source_ref", *REGIME_FIELDS]
    vals = [signal_id, st.value, engine.value, ticker, ts_emitted,
            json.dumps(payload) if payload is not None else None,
            confidence, why, source_ref,
            *(regime[f] for f in REGIME_FIELDS)]
    placeholders = ",".join("?" * len(cols))

    before = conn.execute("SELECT COUNT(*) FROM signals").fetchone()[0]
    conn.execute(
        f"INSERT INTO signals ({','.join(cols)}) VALUES ({placeholders}) "
        f"ON CONFLICT (signal_type, ticker, ts_emitted) DO NOTHING",
        vals,
    )
    after = conn.execute("SELECT COUNT(*) FROM signals").fetchone()[0]
    if after == before:
        return None  # dedup'd

    conn.executemany(
        "INSERT INTO signal_outcomes (signal_id, horizon_days) VALUES (?, ?)",
        [(signal_id, h) for h in HORIZONS_DAYS],
    )
    return signal_id
