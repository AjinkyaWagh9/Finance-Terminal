from __future__ import annotations
from typing import TypedDict
import duckdb

class FeatureCell(TypedDict):
    value: float | None
    is_missing: bool

def upsert_features(conn: duckdb.DuckDBPyConnection,
                    signal_id: str,
                    features: dict[str, FeatureCell]) -> None:
    """Upsert all features for a signal in one batch. Overwrite semantics
    (idempotent re-emit will refresh values, though emit_signal short-circuits
    duplicate signals before reaching here)."""
    if not features:
        return
    rows = [(signal_id, name, cell["value"], cell["is_missing"])
            for name, cell in features.items()]
    conn.executemany(
        """
        INSERT INTO signal_features (signal_id, feature_name, feature_value, is_missing)
        VALUES (?, ?, ?, ?)
        ON CONFLICT (signal_id, feature_name) DO UPDATE SET
            feature_value = EXCLUDED.feature_value,
            is_missing    = EXCLUDED.is_missing
        """,
        rows,
    )
