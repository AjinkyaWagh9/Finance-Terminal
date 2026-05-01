from __future__ import annotations
import math
from datetime import datetime, timedelta

import pytest

from finterminal.data.duckdb_store import connect

TS = datetime(2026, 5, 1, 10, 0)
EXPECTED_VERSION = "reflexivity_v1_vader_decay_0.5"


def _seed_story(conn, headline: str, pub_at: datetime,
                ticker: str = "TCS", fetched_at: datetime | None = None) -> None:
    import uuid
    story_id = str(uuid.uuid4())
    conn.execute(
        """
        INSERT OR IGNORE INTO news_stories
            (id, url, source, headline, body, published_at, fetched_at, tickers, sectors)
        VALUES (?, ?, 'test', ?, NULL, ?, ?, ?, [])
        """,
        [story_id, f"http://x/{headline[:30]}", headline, pub_at,
         fetched_at if fetched_at is not None else pub_at, [ticker]],
    )


# ── sentiment_level ──────────────────────────────────────────────────────────

from finterminal.features.compute_reflexivity import (
    compute_sentiment_level,
    FEATURE_VERSION,
)


def test_sentiment_level_version_constant_matches_expected():
    assert FEATURE_VERSION == EXPECTED_VERSION


def test_sentiment_level_missing_when_no_articles(tmp_path):
    conn = connect(str(tmp_path / "t.duckdb"))
    cell = compute_sentiment_level(conn, ticker="TCS", ts_emitted=TS)
    assert cell["is_missing"] is True and cell["value"] is None
    assert cell["feature_version"] == FEATURE_VERSION


def test_sentiment_level_missing_when_fewer_than_5_articles(tmp_path):
    conn = connect(str(tmp_path / "t.duckdb"))
    for i in range(4):
        _seed_story(conn, f"good news {i}", TS - timedelta(days=i))
    cell = compute_sentiment_level(conn, ticker="TCS", ts_emitted=TS)
    assert cell["is_missing"] is True


def test_sentiment_level_returns_value_with_5_articles(tmp_path):
    conn = connect(str(tmp_path / "t.duckdb"))
    positive_headlines = [
        "strong profit growth rally",
        "company posts record earnings beat",
        "shares surge on upbeat outlook",
        "revenue jumps as demand stays robust",
        "management raises guidance for the year",
        "stock soars after blowout quarter",
    ]
    for i in range(5):
        _seed_story(conn, positive_headlines[i % len(positive_headlines)], TS - timedelta(hours=i * 12))
    cell = compute_sentiment_level(conn, ticker="TCS", ts_emitted=TS)
    assert cell["is_missing"] is False
    assert isinstance(cell["value"], float)
    assert cell["n_samples"] == 5
    assert cell["confidence"] == pytest.approx(0.5)
    assert cell["feature_version"] == FEATURE_VERSION
    assert cell["normalized"] is False
    assert "debug" in cell


def test_sentiment_level_confidence_caps_at_1(tmp_path):
    conn = connect(str(tmp_path / "t.duckdb"))
    positive_headlines = [
        "strong profit growth rally",
        "company posts record earnings beat",
        "shares surge on upbeat outlook",
        "revenue jumps as demand stays robust",
        "management raises guidance for the year",
        "stock soars after blowout quarter",
        "earnings surprise to the upside today",
        "bullish outlook boosts investor confidence",
        "strong cash flow supports growth plans",
        "acquisition deal unlocks significant value",
        "margin expansion delights wall street",
        "dividend hike signals management confidence",
    ]
    # Use 12 unique headlines so unique_ratio = 12/12 = 1.0
    for i in range(12):
        _seed_story(conn, positive_headlines[i], TS - timedelta(hours=i * 6))
    cell = compute_sentiment_level(conn, ticker="TCS", ts_emitted=TS)
    assert cell["confidence"] == pytest.approx(1.0)


def test_sentiment_level_ignores_future_articles(tmp_path):
    conn = connect(str(tmp_path / "t.duckdb"))
    positive_headlines = [
        "strong profit growth rally",
        "company posts record earnings beat",
        "shares surge on upbeat outlook",
        "revenue jumps as demand stays robust",
        "management raises guidance for the year",
        "stock soars after blowout quarter",
    ]
    for i in range(5):
        _seed_story(conn, positive_headlines[i % len(positive_headlines)], TS - timedelta(hours=i * 12))
    cell_before = compute_sentiment_level(conn, ticker="TCS", ts_emitted=TS)
    for i in range(10):
        _seed_story(conn, f"crash bankruptcy crisis {i}", TS + timedelta(days=i + 1))
    cell_after = compute_sentiment_level(conn, ticker="TCS", ts_emitted=TS)
    assert cell_before["value"] == pytest.approx(cell_after["value"])


def test_sentiment_level_excludes_late_arriving_articles(tmp_path):
    """Article published BEFORE ts but FETCHED AFTER ts must be excluded.
    Without this, ingestion-time leakage poisons replay."""
    conn = connect(str(tmp_path / "t.duckdb"))
    # 5 valid articles (published+fetched before ts)
    positive_headlines = [
        "strong profit growth rally",
        "company posts record earnings beat",
        "shares surge on upbeat outlook",
        "revenue jumps as demand stays robust",
        "management raises guidance for the year",
        "stock soars after blowout quarter",
    ]
    for i in range(5):
        _seed_story(conn, positive_headlines[i % len(positive_headlines)], TS - timedelta(hours=i * 12))
    cell_clean = compute_sentiment_level(conn, ticker="TCS", ts_emitted=TS)

    # Now insert "late-arriving" articles: published BEFORE ts (eligible by
    # naive snapshot) but fetched AFTER ts. They must NOT change the value.
    for i in range(20):
        _seed_story(
            conn,
            f"hidden disaster bankruptcy crash {i}",
            pub_at=TS - timedelta(hours=1),
            fetched_at=TS + timedelta(days=1 + i),
        )
    cell_with_late = compute_sentiment_level(conn, ticker="TCS", ts_emitted=TS)
    assert cell_clean["value"] == pytest.approx(cell_with_late["value"]), (
        "late-arriving articles leaked into snapshot — fetched_at filter missing")


def test_sentiment_level_ignores_other_tickers(tmp_path):
    conn = connect(str(tmp_path / "t.duckdb"))
    positive_headlines = [
        "strong profit growth rally",
        "company posts record earnings beat",
        "shares surge on upbeat outlook",
        "revenue jumps as demand stays robust",
        "management raises guidance for the year",
        "stock soars after blowout quarter",
    ]
    for i in range(5):
        _seed_story(conn, positive_headlines[i % len(positive_headlines)], TS - timedelta(hours=i * 12), ticker="INFY")
    cell = compute_sentiment_level(conn, ticker="TCS", ts_emitted=TS)
    assert cell["is_missing"] is True


# ── sentiment_delta ──────────────────────────────────────────────────────────

from finterminal.features.compute_reflexivity import compute_sentiment_delta


def _seed_positive_window(conn, ts_anchor, ticker="TCS", count=6):
    positive_headlines = [
        "strong profit growth rally",
        "company posts record earnings beat",
        "shares surge on upbeat outlook",
        "revenue jumps as demand stays robust",
        "management raises guidance for the year",
        "stock soars after blowout quarter",
    ]
    for i in range(count):
        _seed_story(conn, positive_headlines[i % len(positive_headlines)],
                    ts_anchor - timedelta(hours=i * 10), ticker=ticker)


def _seed_negative_window(conn, ts_anchor, ticker="TCS", count=6):
    negative_headlines = [
        "loss widens as costs rise sharply",
        "shares plunge on weak guidance",
        "company faces bankruptcy risk amid debt crisis",
        "revenue collapses missing all forecasts",
        "stock crashes after dismal quarter",
        "credit downgrade deepens default fears",
    ]
    for i in range(count):
        _seed_story(conn, negative_headlines[i % len(negative_headlines)],
                    ts_anchor - timedelta(hours=i * 10), ticker=ticker)


def test_sentiment_delta_missing_when_current_window_fails(tmp_path):
    conn = connect(str(tmp_path / "t.duckdb"))
    _seed_positive_window(conn, TS - timedelta(days=7))
    cell = compute_sentiment_delta(conn, ticker="TCS", ts_emitted=TS)
    assert cell["is_missing"] is True


def test_sentiment_delta_missing_when_prior_window_fails(tmp_path):
    conn = connect(str(tmp_path / "t.duckdb"))
    _seed_positive_window(conn, TS)
    cell = compute_sentiment_delta(conn, ticker="TCS", ts_emitted=TS)
    assert cell["is_missing"] is True


def test_sentiment_delta_positive_when_sentiment_improves(tmp_path):
    conn = connect(str(tmp_path / "t.duckdb"))
    _seed_negative_window(conn, TS - timedelta(days=7))
    _seed_positive_window(conn, TS)
    cell = compute_sentiment_delta(conn, ticker="TCS", ts_emitted=TS)
    assert cell["is_missing"] is False
    assert cell["value"] > 0
    assert cell["feature_version"] == FEATURE_VERSION


def test_sentiment_delta_negative_when_sentiment_deteriorates(tmp_path):
    conn = connect(str(tmp_path / "t.duckdb"))
    _seed_positive_window(conn, TS - timedelta(days=7))
    _seed_negative_window(conn, TS)
    cell = compute_sentiment_delta(conn, ticker="TCS", ts_emitted=TS)
    assert cell["is_missing"] is False
    assert cell["value"] < 0
