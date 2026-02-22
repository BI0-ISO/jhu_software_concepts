"""
Tests for the query_cli entry point.

We monkeypatch the query functions to avoid hitting the database.
"""

import pytest
from pathlib import Path

import M3_material.query_cli as query_cli

pytestmark = pytest.mark.analysis


def test_query_cli_main_output(monkeypatch, capsys):
    # Provide deterministic values for all query helpers.
    monkeypatch.setattr(query_cli, "count_fall_2026_entries", lambda *_: 2)
    monkeypatch.setattr(query_cli, "percent_international_students", lambda *_: 50.0)
    monkeypatch.setattr(query_cli, "average_metrics_all_applicants", lambda *_: {
        "avg_gpa": 3.8,
        "avg_gre": 160,
        "avg_gre_v": 155,
        "avg_gre_aw": 4.0,
    })
    monkeypatch.setattr(query_cli, "avg_gpa_american_fall_2026", lambda *_: 3.9)
    monkeypatch.setattr(query_cli, "acceptance_rate_fall_2026", lambda *_: 100.0)
    monkeypatch.setattr(query_cli, "avg_gpa_acceptances_fall_2026", lambda *_: 3.7)
    monkeypatch.setattr(query_cli, "count_jhu_masters_cs", lambda *_: 1)
    monkeypatch.setattr(query_cli, "count_top_phd_acceptances_2026_raw_university", lambda *_: 0)
    monkeypatch.setattr(query_cli, "count_top_phd_acceptances_2026_llm", lambda *_: 0)
    monkeypatch.setattr(query_cli, "additional_question_1", lambda *_: 25.0)
    monkeypatch.setattr(query_cli, "additional_question_2", lambda *_: 150.0)

    query_cli.main()
    out = capsys.readouterr().out

    # Validate a few representative lines.
    assert "There are 2 application entries" in out
    assert "50.0% of all applications" in out
    assert "average GRE Quant score is 160" in out
    assert "Additional Question 1 Result" in out


def test_query_cli_script_fallback_imports(monkeypatch):
    # Run the module as a script to exercise fallback imports and __main__.
    import runpy
    import types
    import sys

    # Provide a fake query_data module so fallback import succeeds.
    fake_q = types.ModuleType("query_data")
    fake_q.count_fall_2026_entries = lambda *_: 0
    fake_q.percent_international_students = lambda *_: 0.0
    fake_q.average_metrics_all_applicants = lambda *_: {"avg_gpa": 0, "avg_gre": 0, "avg_gre_v": 0, "avg_gre_aw": 0}
    fake_q.avg_gpa_american_fall_2026 = lambda *_: 0
    fake_q.acceptance_rate_fall_2026 = lambda *_: 0.0
    fake_q.avg_gpa_acceptances_fall_2026 = lambda *_: 0
    fake_q.count_jhu_masters_cs = lambda *_: 0
    fake_q.count_top_phd_acceptances_2026_raw_university = lambda *_: 0
    fake_q.count_top_phd_acceptances_2026_llm = lambda *_: 0
    fake_q.additional_question_1 = lambda *_: 0.0
    fake_q.additional_question_2 = lambda *_: 0.0

    monkeypatch.setitem(sys.modules, "query_data", fake_q)

    root = Path(__file__).resolve().parents[1]
    runpy.run_path(str(root / "src" / "M3_material" / "query_cli.py"), run_name="__main__")
