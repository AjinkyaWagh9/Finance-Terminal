"""News pipeline orchestrator. Runs all steps and persists to DuckDB."""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import date, timedelta

import duckdb

from .collector import fetch_all
from .dedupe import drop_url_dupes, minhash_filter
from .embedder import embed
from .cluster import cluster_stories
from .lineage import match_clusters
from .tagger import tag
from ..data import news_store

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    as_of: date
    n_stories: int
    n_clusters: int
    n_lineage_links: int
    runtime_s: float


def run(conn: duckdb.DuckDBPyConnection) -> PipelineResult:
    """Run the full news pipeline and persist results. Returns PipelineResult."""
    t0 = time.monotonic()
    today = date.today()

    # 1. Collect
    raw_stories = fetch_all()
    logger.info("collected %d raw stories", len(raw_stories))

    if not raw_stories:
        return PipelineResult(
            as_of=today, n_stories=0, n_clusters=0,
            n_lineage_links=0, runtime_s=time.monotonic() - t0,
        )

    # 2. Dedupe
    stories = drop_url_dupes(raw_stories)
    stories = minhash_filter(stories)
    logger.info("%d stories after dedupe", len(stories))

    # 3. Tag
    stories = tag(stories)

    # 4. Embed
    headlines = [s.headline for s in stories]
    embeddings = embed(headlines)
    for s, emb in zip(stories, embeddings):
        s.embedding = emb.tolist()

    # 5. Cluster
    clusters = cluster_stories(stories)
    logger.info("%d clusters formed", len(clusters))

    # 6. Persist stories + clusters
    news_store.upsert_stories(conn, stories)
    news_store.upsert_clusters(conn, clusters, today)

    # 7. Lineage — match today's clusters to yesterday's
    yesterday = today - timedelta(days=1)
    yesterday_clusters = news_store.clusters_for_as_of(conn, yesterday)
    links = match_clusters(yesterday_clusters, clusters, today)
    news_store.upsert_lineage(conn, links)
    logger.info("%d lineage links created", len(links))

    return PipelineResult(
        as_of=today,
        n_stories=len(stories),
        n_clusters=len(clusters),
        n_lineage_links=len(links),
        runtime_s=time.monotonic() - t0,
    )
