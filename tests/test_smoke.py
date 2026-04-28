"""Phase 1 smoke tests. Verifies imports + LLM abstraction loads correctly."""

from __future__ import annotations

import os

import pytest


def test_package_imports():
    import finterminal

    assert finterminal.__version__ == "0.1.0"


def test_llm_abstraction_loads():
    from finterminal.llm import build_router

    router = build_router()
    assert router is not None


def test_supervisor_resolves_to_a_provider():
    """Without ANTHROPIC_API_KEY set, the lookup raises a clear error."""
    from finterminal.llm import ProviderError, build_router

    router = build_router()
    if not os.environ.get("ANTHROPIC_API_KEY"):
        with pytest.raises(ProviderError, match="ANTHROPIC_API_KEY"):
            router.for_agent("supervisor")
    else:
        provider = router.for_agent("supervisor")
        assert provider.metadata.name == "claude-sonnet-4-6"


def test_unknown_agent_errors_clearly():
    from finterminal.llm import AgentNotConfigured, build_router

    router = build_router()
    with pytest.raises(AgentNotConfigured):
        router.for_agent("nonexistent_agent")


def test_duckdb_migration_runs():
    """Opens a fresh DB and confirms tables were created."""
    import tempfile

    from finterminal.data.duckdb_store import get_conn

    with tempfile.TemporaryDirectory() as tmp:
        os.environ["DUCKDB_PATH"] = f"{tmp}/test.duckdb"
        conn = get_conn()
        tables = {r[0] for r in conn.execute("SHOW TABLES").fetchall()}
        assert {"quotes", "fundamentals", "news", "watchlist", "analyses"}.issubset(tables)


def test_nse_normalize():
    from finterminal.data.nse import normalize_ticker

    assert normalize_ticker("RELIANCE") == "RELIANCE.NS"
    assert normalize_ticker("RELIANCE.NS") == "RELIANCE.NS"
    assert normalize_ticker("hdfc", "BSE") == "HDFC.BO"
