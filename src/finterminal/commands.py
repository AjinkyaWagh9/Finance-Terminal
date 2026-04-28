"""Command dispatcher for the REPL.

Each handler takes (args: list[str], console: Console) and renders to the console.
Keeping this sync; LLM-using handlers wrap their async call with asyncio.run().
"""

from __future__ import annotations

import asyncio
import logging

from rich.console import Console

from .data import duckdb_store, openbb_client
from .data.nse import normalize_ticker
from .ui import panels

logger = logging.getLogger(__name__)


def dispatch(line: str, console: Console) -> None:
    parts = line.split()
    if not parts:
        return
    cmd = parts[0]
    args = parts[1:]

    handler = _COMMANDS.get(cmd)
    if handler is None:
        console.print(panels.error_panel(f"unknown command: {cmd}. type /help"))
        return
    try:
        handler(args, console)
    except _UsageError as exc:
        console.print(panels.error_panel(str(exc), title="usage"))
    except Exception as exc:  # noqa: BLE001 — last-resort REPL guard
        logger.exception("command %s failed", cmd)
        console.print(panels.error_panel(f"{type(exc).__name__}: {exc}"))


class _UsageError(Exception):
    pass


def _require_one(args: list[str], usage: str) -> str:
    if len(args) != 1:
        raise _UsageError(usage)
    return args[0]


# ---------- /help ----------


def _cmd_help(args: list[str], console: Console) -> None:
    console.print(panels.help_panel())


# ---------- /ticker ----------


def _cmd_ticker(args: list[str], console: Console) -> None:
    raw = _require_one(args, "/ticker SYMBOL  (e.g. /ticker RELIANCE)")
    ticker = normalize_ticker(raw)

    with console.status(f"fetching {ticker}…", spinner="dots"):
        quote = openbb_client.fetch_quote(ticker)
        try:
            fundamentals = openbb_client.fetch_fundamentals(ticker)
        except Exception as exc:  # noqa: BLE001 — fundamentals are best-effort
            logger.warning("fundamentals unavailable for %s: %s", ticker, exc)
            fundamentals = None

    conn = duckdb_store.get_conn()
    try:
        duckdb_store.upsert_quote(conn, quote)
        if fundamentals:
            duckdb_store.upsert_fundamentals(conn, fundamentals)
    finally:
        conn.close()

    console.print(panels.ticker_panel(quote, fundamentals))


# ---------- /news ----------


def _cmd_news(args: list[str], console: Console) -> None:
    raw = _require_one(args, "/news SYMBOL  (e.g. /news INFY)")
    ticker = normalize_ticker(raw)

    with console.status(f"fetching news for {ticker}…", spinner="dots"):
        try:
            items = openbb_client.fetch_news(ticker, limit=20)
        except RuntimeError as exc:
            # yfinance returns Empty for many Indian tickers; render as empty rather than error.
            # Phase 2 adds an RSS aggregator (Mint, MoneyControl, ET) per PLAN.md §4.4.
            logger.info("news empty for %s: %s", ticker, exc)
            items = []

    if items:
        conn = duckdb_store.get_conn()
        try:
            duckdb_store.upsert_news(conn, items)
        finally:
            conn.close()

    console.print(panels.news_table(items, ticker))


# ---------- /watch ----------


def _cmd_watch(args: list[str], console: Console) -> None:
    if not args:
        raise _UsageError("/watch add SYMBOL | /watch list | /watch remove SYMBOL")
    sub = args[0]
    rest = args[1:]
    conn = duckdb_store.get_conn()
    try:
        if sub == "list":
            if rest:
                raise _UsageError("/watch list  (no args)")
            console.print(panels.watchlist_table(duckdb_store.list_watchlist(conn)))
            return
        if sub == "add":
            if not rest:
                raise _UsageError("/watch add SYMBOL [notes...]")
            ticker = normalize_ticker(rest[0])
            notes = " ".join(rest[1:]) if len(rest) > 1 else None
            duckdb_store.add_to_watchlist(conn, ticker, notes)
            console.print(panels.info_panel(f"added [bold]{ticker}[/]"))
            return
        if sub == "remove":
            if len(rest) != 1:
                raise _UsageError("/watch remove SYMBOL")
            ticker = normalize_ticker(rest[0])
            duckdb_store.remove_from_watchlist(conn, ticker)
            console.print(panels.info_panel(f"removed [bold]{ticker}[/]"))
            return
        raise _UsageError(f"unknown subcommand: {sub}")
    finally:
        conn.close()


# ---------- /analyze ----------


def _cmd_analyze(args: list[str], console: Console) -> None:
    raw = _require_one(args, "/analyze SYMBOL  (e.g. /analyze RELIANCE)")
    ticker = normalize_ticker(raw)

    from .agents.supervisor import analyze_ticker

    conn = duckdb_store.get_conn()
    try:
        with console.status(
            f"analyzing {ticker} (Claude supervisor)…", spinner="dots"
        ):
            result = asyncio.run(analyze_ticker(ticker, conn))
    finally:
        conn.close()

    console.print(panels.analysis_panel(result))


_COMMANDS = {
    "/help": _cmd_help,
    "/ticker": _cmd_ticker,
    "/news": _cmd_news,
    "/watch": _cmd_watch,
    "/analyze": _cmd_analyze,
}
