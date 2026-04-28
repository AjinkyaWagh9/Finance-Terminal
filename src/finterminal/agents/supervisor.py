"""Supervisor agent — orchestrates /analyze.

Phase 1: single-call flow. Fetches quote + fundamentals + news, formats a context
block with [src: ...] tags, calls the supervisor LLM (Claude per agents.yaml), and
parses the structured response into the `analyses` schema.

Phase 2 splits this into delegated specialists; the contract here doesn't change.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

import duckdb

from ..data import duckdb_store, openbb_client
from ..llm import Message, build_router
from ..llm.budget import record
from ..ui.panels import build_context_block

logger = logging.getLogger(__name__)

_PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "analyst.md"


_SECTIONS = (
    "Bull Case",
    "Bear Case",
    "Confidence",
    "Assumptions",
    "What Would Change My Mind",
)


def _load_system_prompt() -> str:
    return _PROMPT_PATH.read_text()


def parse_analysis(text: str) -> dict:
    """Splits the analyst's structured response into fields.

    Lenient: missing sections become empty strings; missing confidence becomes None.
    Confidence parses the first float in the section.
    """
    pattern = re.compile(
        r"^##\s+(" + "|".join(re.escape(s) for s in _SECTIONS) + r")\s*$",
        re.MULTILINE,
    )
    matches = list(pattern.finditer(text))
    sections: dict[str, str] = {}
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        sections[m.group(1)] = text[start:end].strip()

    confidence: float | None = None
    raw_conf = sections.get("Confidence", "")
    if raw_conf:
        m = re.search(r"-?\d+(?:\.\d+)?", raw_conf)
        if m:
            try:
                v = float(m.group(0))
                confidence = max(0.0, min(1.0, v))
            except ValueError:
                confidence = None

    return {
        "bull_case": sections.get("Bull Case", ""),
        "bear_case": sections.get("Bear Case", ""),
        "confidence": confidence,
        "assumptions": sections.get("Assumptions", ""),
        "what_would_change": sections.get("What Would Change My Mind", ""),
    }


async def analyze_ticker(ticker: str, conn: duckdb.DuckDBPyConnection) -> dict:
    """Fetch context, call the supervisor LLM, parse, persist. Returns the parsed dict.

    Network calls are made fresh on each invocation (no cache layer in Phase 1).
    """
    quote: dict | None = None
    fundamentals: dict | None = None
    news: list[dict] = []

    try:
        quote = openbb_client.fetch_quote(ticker)
        duckdb_store.upsert_quote(conn, quote)
    except Exception as exc:  # noqa: BLE001 — surface to caller as analysis-level error
        raise RuntimeError(f"quote fetch failed: {exc}") from exc

    try:
        fundamentals = openbb_client.fetch_fundamentals(ticker)
        duckdb_store.upsert_fundamentals(conn, fundamentals)
    except Exception as exc:  # noqa: BLE001
        logger.warning("fundamentals unavailable for %s: %s", ticker, exc)

    try:
        news = openbb_client.fetch_news(ticker, limit=10)
        if news:
            duckdb_store.upsert_news(conn, news)
    except Exception as exc:  # noqa: BLE001
        logger.warning("news unavailable for %s: %s", ticker, exc)

    context_block = build_context_block(ticker, quote, fundamentals, news)
    user_message = (
        context_block
        + "\n\nProduce the analysis per your output format. "
        "Every numeric claim must trace to a [src: ...] tag from the context above."
    )

    router = build_router()
    llm = router.for_agent("supervisor")
    completion = await llm.complete(
        system=_load_system_prompt(),
        messages=[Message(role="user", content=user_message)],
        max_tokens=2000,
        temperature=0.3,
    )

    record("supervisor", completion)

    parsed = parse_analysis(completion.text)
    parsed["ticker"] = ticker

    sources = {
        "quote_provider": quote.get("provider") if quote else None,
        "fundamentals_provider": fundamentals.get("provider") if fundamentals else None,
        "news_count": len(news),
        "model": completion.model,
        "tokens_in": completion.tokens_in,
        "tokens_out": completion.tokens_out,
    }
    aid = duckdb_store.record_analysis(
        conn,
        ticker=ticker,
        bull_case=parsed["bull_case"],
        bear_case=parsed["bear_case"],
        confidence=parsed["confidence"] if parsed["confidence"] is not None else 0.0,
        sources=sources,
    )
    parsed["analysis_id"] = aid
    return parsed
