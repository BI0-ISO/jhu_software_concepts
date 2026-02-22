"""
Tests for the legacy bulk-scrape runner in M2_material/main.py.

We mock the scraper and cleaner to avoid live network calls.
"""

import pytest
from pathlib import Path

from M2_material import main as m2_main

pytestmark = pytest.mark.analysis


def test_m2_main_runs_with_mocked_scraper(monkeypatch, tmp_path):
    # Provide a small, deterministic set of fake pages.
    fake_pages = [
        {"url": "https://www.thegradcafe.com/result/1", "html": "<div>ok</div>", "date_added": "2026-01-01"},
        {"url": "https://www.thegradcafe.com/result/2", "html": "<div>ok</div>", "date_added": "2026-01-02"},
    ]

    monkeypatch.setattr(m2_main, "START_ENTRY", 1)
    monkeypatch.setattr(m2_main, "END_ENTRY", 3)
    monkeypatch.setattr(m2_main, "TOTAL_VALID_ENTRIES", 2)
    monkeypatch.setattr(m2_main, "CHUNK_SIZE", 1)
    monkeypatch.setattr(m2_main, "OUTPUT_FILE", str(tmp_path / "out.json"))

    # Fake the scraper to return our pages in order.
    monkeypatch.setattr(m2_main, "scrape_data", lambda *args, **kwargs: iter(fake_pages))

    # Fake cleaner returns a simple dict per page.
    monkeypatch.setattr(m2_main, "clean_data", lambda pages: [{"url": pages[0]["url"]}])

    saved = {"calls": 0}

    def fake_save(data, filename):
        saved["calls"] += 1
        # Ensure the save target is the configured output file.
        assert filename == str(tmp_path / "out.json")

    monkeypatch.setattr(m2_main, "save_data", fake_save)

    # Execute main; it should auto-save and final-save without errors.
    m2_main.main()
    assert saved["calls"] >= 2


def test_m2_main_script_fallback_imports(monkeypatch, tmp_path):
    # Execute the module as a script to exercise the fallback import path
    # (the relative imports will fail and the except branch will run).
    import runpy
    import types
    import sys

    # Provide fake top-level modules that the fallback import will use.
    fake_scrape = types.ModuleType("scrape")
    fake_clean = types.ModuleType("clean")

    # Return an empty iterator to avoid long loops.
    fake_scrape.scrape_data = lambda *a, **k: iter([])
    fake_clean.clean_data = lambda pages: []
    fake_clean.save_data = lambda *a, **k: None

    monkeypatch.setitem(sys.modules, "scrape", fake_scrape)
    monkeypatch.setitem(sys.modules, "clean", fake_clean)

    # Run the module as __main__ to hit the guard and the fallback imports.
    root = Path(__file__).resolve().parents[1]
    runpy.run_path(str(root / "src" / "M2_material" / "main.py"), run_name="__main__")
