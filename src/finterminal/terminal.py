"""REPL entrypoint. Day 4 fills in command dispatch."""

from __future__ import annotations

from dotenv import load_dotenv
from rich.console import Console

from .ui.panels import banner

load_dotenv()
console = Console()


def run() -> None:
    console.print(banner())
    while True:
        try:
            line = console.input("[bold green]>[/] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]bye.[/]")
            return
        if not line:
            continue
        if line in ("/quit", "/exit"):
            console.print("[dim]bye.[/]")
            return
        if line == "/help":
            console.print(
                "[bold]Phase 1 commands (Day 4 will wire them up):[/]\n"
                "  /ticker SYMBOL\n  /news SYMBOL\n  /watch add|list|remove SYMBOL\n"
                "  /analyze SYMBOL\n  /quit"
            )
            continue
        console.print(f"[yellow]not implemented yet:[/] {line}")


if __name__ == "__main__":
    run()
