"""DuckDB connection + migrations. Day 3 fills in upsert/query helpers."""

from __future__ import annotations

import os
from pathlib import Path

import duckdb

_MIGRATIONS_DIR = Path(__file__).parent / "migrations"


def _db_path() -> Path:
    raw = os.environ.get("DUCKDB_PATH", "./data/finterminal.duckdb")
    p = Path(raw).resolve()
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def get_conn() -> duckdb.DuckDBPyConnection:
    """Returns a DuckDB connection. Runs migrations on first open."""
    conn = duckdb.connect(str(_db_path()))
    _run_migrations(conn)
    return conn


def _run_migrations(conn: duckdb.DuckDBPyConnection) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS _migrations (id VARCHAR PRIMARY KEY, applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
    )
    applied = {row[0] for row in conn.execute("SELECT id FROM _migrations").fetchall()}
    for sql_file in sorted(_MIGRATIONS_DIR.glob("*.sql")):
        if sql_file.stem in applied:
            continue
        conn.execute(sql_file.read_text())
        conn.execute("INSERT INTO _migrations (id) VALUES (?)", [sql_file.stem])
