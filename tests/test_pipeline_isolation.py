# tests/test_pipeline_isolation.py
import pathlib

ROOT = pathlib.Path(__file__).parents[1] / "src" / "finterminal" / "market_data"

def test_market_data_does_not_import_outcomes():
    offenders = []
    for p in ROOT.rglob("*.py"):
        text = p.read_text()
        if "from finterminal.outcomes" in text or "import finterminal.outcomes" in text:
            offenders.append(str(p))
    assert not offenders, f"market_data must not import outcomes: {offenders}"
