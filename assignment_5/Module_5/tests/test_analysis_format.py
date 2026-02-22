"""
Tests focused on analysis formatting and data structures.

These are "analysis" tests because they verify the UI output and
the shape of the computed results returned by query helpers.
"""

import re

import pytest
from bs4 import BeautifulSoup

from M3_material.query_data import build_analysis_results


@pytest.mark.analysis
def test_percentage_formatting_two_decimals(app, client, sample_record, insert_records):
    # Seed the database with a mix of international and domestic records
    # to exercise percent formatting and answer labels.
    records = [
        sample_record(url="https://www.thegradcafe.com/result/999010", us_or_international="International"),
        sample_record(url="https://www.thegradcafe.com/result/999011", us_or_international="International", gpa=3.6),
        sample_record(url="https://www.thegradcafe.com/result/999012", us_or_international="American", gpa=None),
    ]
    insert_records(records)

    # Render the page and capture all percentage strings in the text.
    # BeautifulSoup parses the HTML so we can inspect the full page text.
    resp = client.get("/analysis")
    assert resp.status_code == 200
    soup = BeautifulSoup(resp.data.decode("utf-8"), "html.parser")
    text = soup.get_text()
    # Find any "NN.NN%" style tokens in the page text.
    percents = re.findall(r"\d+(?:\.\d+)?%", text)
    assert percents
    # Enforce two-decimal precision across all percentages.
    assert all(re.match(r"^\d+\.\d{2}%$", p) for p in percents)
    # "Answer:" labels are required by the assignment spec.
    assert "Answer:" in text


@pytest.mark.analysis
def test_analysis_results_keys(sample_record, insert_records):
    # Insert one record so analysis functions return populated structures.
    insert_records([sample_record()])
    results = build_analysis_results()
    # Top-level keys used by templates and reporting.
    assert set(results.keys()) == {"total_applicants", "year_2026", "all_time"}

    # Required keys for the "2026 cohort" section.
    year_keys = {
        "fall_2026_count",
        "percent_international",
        "average_metrics",
        "avg_gpa_american_fall_2026",
        "acceptance_rate_fall_2026",
        "avg_gpa_acceptances_fall_2026",
        "jhu_masters_cs",
        "top_phd_acceptances_2026_raw",
        "top_phd_acceptances_2026_llm",
        "additional_question_1",
        "additional_question_2",
    }
    assert year_keys.issubset(results["year_2026"].keys())
    # "all_time" uses total_entries (not fall_2026_count), but otherwise
    # should expose the same analysis keys used in the template.
    all_time_keys = set(year_keys) - {"fall_2026_count"}
    all_time_keys.add("total_entries")
    assert all_time_keys.issubset(results["all_time"].keys())

    # Nested metrics dictionary must include all expected averages.
    metrics = results["year_2026"]["average_metrics"]
    assert {"avg_gpa", "avg_gre", "avg_gre_v", "avg_gre_aw"}.issubset(metrics.keys())
