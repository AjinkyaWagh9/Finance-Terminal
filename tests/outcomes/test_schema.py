import duckdb
from finterminal.data.duckdb_store import connect


def test_migration_004_creates_all_tables(tmp_path):
    db_path = tmp_path / "t.duckdb"
    conn = connect(str(db_path))
    tables = {r[0] for r in conn.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema='main'"
    ).fetchall()}
    for t in ("signals", "signal_outcomes", "prices_eod", "ingestion_log"):
        assert t in tables, f"missing table: {t}"


def test_signals_unique_constraint(tmp_path):
    conn = connect(str(tmp_path / "t.duckdb"))
    conn.execute("""
        INSERT INTO signals (signal_id, signal_type, engine, ticker, ts_emitted)
        VALUES ('a', 'cluster_momentum', 'reflexivity', 'TCS', '2026-04-29 10:00:00')
    """)
    import pytest, duckdb
    with pytest.raises(duckdb.ConstraintException):
        conn.execute("""
            INSERT INTO signals (signal_id, signal_type, engine, ticker, ts_emitted)
            VALUES ('b', 'cluster_momentum', 'reflexivity', 'TCS', '2026-04-29 10:00:00')
        """)
