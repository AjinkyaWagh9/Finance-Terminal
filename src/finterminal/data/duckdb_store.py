"""DuckDB connection + CRUD helpers."""

from __future__ import annotations

import json
import os
import uuid
from datetime import date, datetime
from pathlib import Path
from typing import Any

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


# ---------- quotes ----------

def upsert_quote(conn: duckdb.DuckDBPyConnection, q: dict) -> None:
    """Insert or replace by (ticker, as_of)."""
    conn.execute(
        """
        INSERT OR REPLACE INTO quotes
            (ticker, as_of, last_price, change_pct, volume, market_cap)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        [
            q["ticker"],
            q["as_of"],
            q.get("last_price"),
            q.get("change_pct"),
            q.get("volume"),
            q.get("market_cap"),
        ],
    )


def latest_quote(conn: duckdb.DuckDBPyConnection, ticker: str) -> dict | None:
    row = conn.execute(
        "SELECT ticker, as_of, last_price, change_pct, volume, market_cap "
        "FROM quotes WHERE ticker = ? ORDER BY as_of DESC LIMIT 1",
        [ticker],
    ).fetchone()
    if not row:
        return None
    return dict(zip(
        ["ticker", "as_of", "last_price", "change_pct", "volume", "market_cap"],
        row,
    ))


# ---------- fundamentals ----------

def upsert_fundamentals(conn: duckdb.DuckDBPyConnection, f: dict) -> None:
    conn.execute(
        """
        INSERT OR REPLACE INTO fundamentals
            (ticker, as_of, pe_ttm, eps_ttm, roe, roce, debt_to_equity, revenue_ttm, net_income_ttm)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            f["ticker"],
            f["as_of"],
            f.get("pe_ttm"),
            f.get("eps_ttm"),
            f.get("roe"),
            f.get("roce"),
            f.get("debt_to_equity"),
            f.get("revenue_ttm"),
            f.get("net_income_ttm"),
        ],
    )


def latest_fundamentals(conn: duckdb.DuckDBPyConnection, ticker: str) -> dict | None:
    row = conn.execute(
        "SELECT ticker, as_of, pe_ttm, eps_ttm, roe, roce, debt_to_equity, revenue_ttm, net_income_ttm "
        "FROM fundamentals WHERE ticker = ? ORDER BY as_of DESC LIMIT 1",
        [ticker],
    ).fetchone()
    if not row:
        return None
    return dict(zip(
        ["ticker", "as_of", "pe_ttm", "eps_ttm", "roe", "roce", "debt_to_equity",
         "revenue_ttm", "net_income_ttm"],
        row,
    ))


# ---------- news ----------

def upsert_news(conn: duckdb.DuckDBPyConnection, items: list[dict]) -> int:
    inserted = 0
    for n in items:
        if not n.get("id"):
            continue
        conn.execute(
            """
            INSERT OR REPLACE INTO news
                (id, ticker, source, headline, url, published_at, body)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                str(n["id"]),
                n.get("ticker"),
                n.get("source"),
                n.get("headline"),
                n.get("url"),
                n.get("published_at"),
                n.get("body"),
            ],
        )
        inserted += 1
    return inserted


def recent_news(conn: duckdb.DuckDBPyConnection, ticker: str, limit: int = 10) -> list[dict]:
    rows = conn.execute(
        "SELECT id, ticker, source, headline, url, published_at, body "
        "FROM news WHERE ticker = ? ORDER BY published_at DESC NULLS LAST LIMIT ?",
        [ticker, limit],
    ).fetchall()
    cols = ["id", "ticker", "source", "headline", "url", "published_at", "body"]
    return [dict(zip(cols, r)) for r in rows]


# ---------- watchlist ----------

def add_to_watchlist(conn: duckdb.DuckDBPyConnection, ticker: str, notes: str | None = None) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO watchlist (ticker, notes) VALUES (?, ?)",
        [ticker, notes],
    )


def remove_from_watchlist(conn: duckdb.DuckDBPyConnection, ticker: str) -> None:
    conn.execute("DELETE FROM watchlist WHERE ticker = ?", [ticker])


def list_watchlist(conn: duckdb.DuckDBPyConnection) -> list[dict]:
    rows = conn.execute(
        "SELECT ticker, added_at, notes FROM watchlist ORDER BY added_at"
    ).fetchall()
    return [dict(zip(["ticker", "added_at", "notes"], r)) for r in rows]


# ---------- analyses (Day 5) ----------

def record_analysis(
    conn: duckdb.DuckDBPyConnection,
    ticker: str,
    bull_case: str,
    bear_case: str,
    confidence: float,
    sources: dict[str, Any] | None = None,
) -> str:
    """Returns the inserted row's id (uuid4)."""
    aid = str(uuid.uuid4())
    conn.execute(
        """
        INSERT INTO analyses (id, ticker, bull_case, bear_case, confidence, sources_json)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        [aid, ticker, bull_case, bear_case, confidence, json.dumps(sources or {})],
    )
    return aid


def latest_analysis(conn: duckdb.DuckDBPyConnection, ticker: str) -> dict | None:
    row = conn.execute(
        "SELECT id, ticker, created_at, bull_case, bear_case, confidence, sources_json "
        "FROM analyses WHERE ticker = ? ORDER BY created_at DESC LIMIT 1",
        [ticker],
    ).fetchone()
    if not row:
        return None
    cols = ["id", "ticker", "created_at", "bull_case", "bear_case", "confidence", "sources_json"]
    out = dict(zip(cols, row))
    out["sources"] = json.loads(out.pop("sources_json") or "{}")
    return out
