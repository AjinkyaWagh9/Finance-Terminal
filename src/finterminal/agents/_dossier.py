"""Compact source dossier for the Critic.

The Analyst gets a full context block (today's `ui.panels.build_context_block`).
The Critic does NOT need the full news-article bodies — it needs to verify
[src: ...] tags from the Analyst's output. A one-line-per-source compact form
saves ~40% of Critic input tokens with no loss in verification accuracy.

Output is a stable, deterministic string — feed it directly to the Critic LLM
as the user message body.
"""
from __future__ import annotations

from typing import Any


def _fmt_or_dash(v: Any, decimals: int = 2) -> str:
    if v is None:
        return "—"
    if isinstance(v, float):
        return f"{v:.{decimals}f}"
    return str(v)


def _render_quote(q: dict) -> str:
    price = _fmt_or_dash(q.get("last_price"))
    chg = q.get("change_pct")
    chg_str = "—" if chg is None else f"{chg:+.2f}%"
    as_of = q.get("as_of")
    provider = q.get("provider", "?")
    return f"[QUOTE]      {q.get('ticker', '?')}  {price}  {chg_str}  {as_of}  (provider: {provider})"


def _render_fundamentals(f: dict | None) -> list[str]:
    if not f:
        return ["[FUND]       fundamentals unavailable"]
    lines: list[str] = []
    pe = f.get("pe_ttm")
    if pe is not None:
        lines.append(f"[FUND-PE]    {_fmt_or_dash(pe)}   (TTM)")
    eps = f.get("eps_ttm")
    if eps is not None:
        lines.append(f"[FUND-EPS]   {_fmt_or_dash(eps)}")
    roe = f.get("roe")
    if roe is not None:
        lines.append(f"[FUND-ROE]   {_fmt_or_dash(roe, 3)}")
    roce = f.get("roce")
    if roce is not None:
        lines.append(f"[FUND-ROCE]  {_fmt_or_dash(roce, 3)}")
    de = f.get("debt_to_equity")
    if de is not None:
        lines.append(f"[FUND-DEBT]  {_fmt_or_dash(de)}   (D/E)")
    rev = f.get("revenue_ttm")
    if rev is not None:
        lines.append(f"[FUND-REV]   {_fmt_or_dash(rev)}")
    ni = f.get("net_income_ttm")
    if ni is not None:
        lines.append(f"[FUND-NI]    {_fmt_or_dash(ni)}")
    if not lines:
        return ["[FUND]       fundamentals unavailable"]
    return lines


def _render_news(news: list[dict]) -> list[str]:
    if not news:
        return ["[NEWS]       no news returned"]
    lines: list[str] = []
    for i, n in enumerate(news, start=1):
        published = n.get("published_at")
        date_str = (
            published.strftime("%Y-%m-%d") if hasattr(published, "strftime")
            else (str(published)[:10] if published else "—")
        )
        source = n.get("source") or "?"
        headline = (n.get("headline") or "—").strip()
        # Truncate very long headlines so the dossier remains compact.
        if len(headline) > 140:
            headline = headline[:137] + "…"
        lines.append(f"[NEWS-{i}]     \"{headline}\"  {source}  {date_str}")
    return lines


def build_source_dossier(
    ticker: str,
    quote: dict,
    fundamentals: dict | None,
    news: list[dict],
) -> str:
    """Returns the compact source dossier string for Critic input."""
    parts: list[str] = [f"SOURCES AVAILABLE TO THE ANALYST ({ticker}):", ""]
    parts.append(_render_quote(quote))
    parts.extend(_render_fundamentals(fundamentals))
    parts.extend(_render_news(news))
    parts.append("")
    parts.append(
        "VERIFY: every numeric or qualitative claim in the analyst's output "
        "should map to one of the [...] tags above. Flag any that does not."
    )
    return "\n".join(parts)
