"""
Tests for PDF report generation helpers.

These validate formatting and that a PDF file is written to disk.
"""

import os

import pytest

from M3_material import reporting

pytestmark = pytest.mark.analysis


def test_sanitize_wrap_and_escape():
    # _sanitize should strip non-ASCII characters.
    assert reporting._sanitize("Hello 🌟") == "Hello  "
    # None should return empty string.
    assert reporting._sanitize(None) == ""

    # _wrap should return a list of lines within the width.
    lines = reporting._wrap("one two three", width=5)
    assert isinstance(lines, list)
    assert lines

    # _escape_pdf should escape PDF control characters.
    assert reporting._escape_pdf("(test)") == "\\(test\\)"


def test_generate_pdf_report(tmp_path):
    # Build a minimal results dict with the keys used in report generation.
    results = {
        "total_applicants": 1,
        "year_2026": {
            "fall_2026_count": 1,
            "percent_international": 50.0,
            "average_metrics": {"avg_gpa": 3.8, "avg_gre": 160, "avg_gre_v": 155, "avg_gre_aw": 4.0},
            "avg_gpa_american_fall_2026": 3.8,
            "acceptance_rate_fall_2026": 100.0,
            "avg_gpa_acceptances_fall_2026": 3.8,
            "jhu_masters_cs": 1,
            "top_phd_acceptances_2026_raw": 0,
            "top_phd_acceptances_2026_llm": 0,
            "additional_question_1": 100.0,
            "additional_question_2": None,
        },
        "all_time": {
            "total_entries": 1,
            "percent_international": 50.0,
            "average_metrics": {"avg_gpa": 3.8, "avg_gre": 160, "avg_gre_v": 155, "avg_gre_aw": 4.0},
            "avg_gpa_american_fall_2026": 3.8,
            "acceptance_rate_fall_2026": 100.0,
            "avg_gpa_acceptances_fall_2026": 3.8,
            "jhu_masters_cs": 1,
            "top_phd_acceptances_2026_raw": 0,
            "top_phd_acceptances_2026_llm": 0,
            "additional_question_1": 100.0,
            "additional_question_2": None,
        },
    }

    out_path = tmp_path / "report.pdf"
    reporting.generate_pdf_report(results, str(out_path))

    # The file should exist and start with a PDF header.
    data = out_path.read_bytes()
    assert data.startswith(b"%PDF")


def test_generate_pdf_report_cwd_path():
    # Writing to a filename without a directory should succeed.
    reporting.generate_pdf_report({"total_applicants": 0, "year_2026": {}, "all_time": {}}, "tmp_report.pdf")
    assert os.path.exists("tmp_report.pdf")
    os.remove("tmp_report.pdf")


def test_generate_db_hardening_report(tmp_path):
    out_path = tmp_path / "hardening.pdf"
    reporting.generate_db_hardening_report(str(out_path))
    data = out_path.read_bytes()
    assert data.startswith(b"%PDF")
