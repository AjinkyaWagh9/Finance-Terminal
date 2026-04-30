from finterminal.data.duckdb_store import connect
from finterminal.features.store import upsert_features

def test_upsert_writes_value_and_missing_rows(tmp_path):
    conn = connect(str(tmp_path / "t.duckdb"))
    upsert_features(conn, "sig1", {
        "mom_7d":    {"value": 0.05, "is_missing": False},
        "vol_20d":   {"value": None, "is_missing": True},
    })
    rows = conn.execute(
        "SELECT feature_name, feature_value, is_missing "
        "FROM signal_features WHERE signal_id=? ORDER BY feature_name",
        ["sig1"],
    ).fetchall()
    assert rows == [("mom_7d", 0.05, False), ("vol_20d", None, True)]

def test_upsert_is_idempotent(tmp_path):
    conn = connect(str(tmp_path / "t.duckdb"))
    upsert_features(conn, "sig1", {"mom_7d": {"value": 0.05, "is_missing": False}})
    upsert_features(conn, "sig1", {"mom_7d": {"value": 0.07, "is_missing": False}})
    rows = conn.execute(
        "SELECT feature_value FROM signal_features WHERE signal_id=?",
        ["sig1"],
    ).fetchall()
    assert rows == [(0.07,)]   # second write wins (overwrite semantics)
