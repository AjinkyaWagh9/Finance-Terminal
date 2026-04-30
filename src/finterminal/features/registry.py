from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Optional

@dataclass(frozen=True)
class FeatureSpec:
    name: str
    compute: Optional[str]   # name of compute function (or None for placeholder)
    source: str              # human-readable provenance

# Tunables: see spec D5.
ZSCORE_WINDOW_DAYS = 60
ZSCORE_MIN_OBS = 30
REGIME_VOL_MEDIAN_LOOKBACK_DAYS = 252

# Freshness gate (D12). G7/G10 from ADR-019.
# A signal emitted at ts_emitted whose most-recent prices_eod row for the
# ticker is older than this many days produces is_missing=true for all
# price-derived features. Same threshold applies to _NIFTY50 for regime.
MAX_PRICE_STALENESS_DAYS = 5
MAX_NIFTY_STALENESS_DAYS = 5

V1_FEATURES: tuple[FeatureSpec, ...] = (
    # Price (compute_price.py)
    FeatureSpec("mom_7d",                  "mom_7d",                   "prices_eod"),
    FeatureSpec("mom_30d",                 "mom_30d",                  "prices_eod"),
    FeatureSpec("vol_20d",                 "vol_20d",                  "prices_eod"),
    FeatureSpec("mom_7d_z",                "mom_7d_z",                 "derived"),
    # Regime (compute_regime.py)
    FeatureSpec("nifty_return_50d",        "nifty_return_50d",         "prices_eod[_NIFTY50]"),
    FeatureSpec("nifty_vol_20d",           "nifty_vol_20d",            "prices_eod[_NIFTY50]"),
    FeatureSpec("regime_bull",             "regime_bull",              "derived"),
    FeatureSpec("regime_bear",             "regime_bear",              "derived"),
    FeatureSpec("regime_volatile",         "regime_volatile",          "derived"),
    # News (compute_news.py)
    FeatureSpec("cluster_momentum_z",      "cluster_momentum_z",       "signals.payload"),
    FeatureSpec("narrative_price_divergence", "narrative_price_divergence", "derived"),
    # Quality placeholders (#3 fills these)
    FeatureSpec("roe",                     None, "fundamentals (#3)"),
    FeatureSpec("leverage",                None, "fundamentals (#3)"),
    FeatureSpec("earnings_growth",         None, "fundamentals (#3)"),
    FeatureSpec("quality_score",           None, "derived (#3)"),
    # Reflexivity placeholders (#4 fills these)
    FeatureSpec("sentiment_level",         None, "Grok / news (#4)"),
    FeatureSpec("sentiment_delta",         None, "derived (#4)"),
    FeatureSpec("entropy_sentiment",       None, "derived (#4)"),
)

COMPUTABLE_NAMES:  tuple[str, ...] = tuple(f.name for f in V1_FEATURES if f.compute is not None)
PLACEHOLDER_NAMES: tuple[str, ...] = tuple(f.name for f in V1_FEATURES if f.compute is None)
