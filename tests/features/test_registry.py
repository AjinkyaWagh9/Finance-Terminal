from finterminal.data.duckdb_store import connect

def test_signal_features_table_exists(tmp_path):
    conn = connect(str(tmp_path / "t.duckdb"))
    cols = conn.execute("PRAGMA table_info('signal_features')").fetchall()
    names = {c[1] for c in cols}
    assert names == {"signal_id", "feature_name", "feature_value", "is_missing"}

def test_signal_features_pk_is_signal_id_and_feature_name(tmp_path):
    conn = connect(str(tmp_path / "t.duckdb"))
    conn.execute(
        "INSERT INTO signal_features VALUES (?, ?, ?, ?)",
        ["s1", "mom_7d", 0.05, False],
    )
    # Duplicate PK must fail
    import duckdb
    try:
        conn.execute(
            "INSERT INTO signal_features VALUES (?, ?, ?, ?)",
            ["s1", "mom_7d", 0.99, False],
        )
        raised = False
    except duckdb.ConstraintException:
        raised = True
    assert raised
