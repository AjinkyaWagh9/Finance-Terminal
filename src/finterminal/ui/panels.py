"""Rich panel renderers. Day 4 fills these in."""

from __future__ import annotations

from rich.panel import Panel


def banner() -> Panel:
    return Panel(
        "[bold cyan]FINTERMINAL[/] v0.1 — Phase 1 bootstrap\n"
        "Type [bold]/help[/] for commands, [bold]/quit[/] to exit.",
        border_style="cyan",
    )


# Day 4 will add: ticker_panel, news_panel, fundamentals_panel, watchlist_panel
