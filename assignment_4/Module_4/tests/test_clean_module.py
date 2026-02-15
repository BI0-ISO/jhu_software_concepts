"""
Additional unit tests for the M2 cleaner helpers.

These cover edge cases and ensure normalization branches are exercised.
"""

import pytest

from M2_material import clean

pytestmark = pytest.mark.analysis


def test_clean_data_parses_fields_and_sanitizes_notes():
    # Construct a minimal HTML snippet that includes all expected fields.
    html = """
    <html><body>
      Program Computer Science
      Institution Johns Hopkins University
      Notes I love it 😊 Timeline
      Decision Accepted on Jan 20
      Accepted on Jan 20, 2026
      Fall 2026
      International
      GRE General: 165
      GRE Verbal: 160
      Analytical Writing: 4.5
      Undergrad GPA: 3.9 GRE General: 165
      Type Masters Degree
    </body></html>
    """
    page = {"html": html, "url": "https://www.thegradcafe.com/result/999200", "date_added": "2026-01-15"}

    record = clean.clean_data([page])[0]

    # The cleaner should extract core fields and sanitize notes (emoji removed).
    assert record["program"] == "Computer Science"
    assert record["university"] == "Johns Hopkins University"
    assert record["comments"] == "I love it"
    assert record["url"] == page["url"]
    assert record["applicant_status"] == "accepted"
    assert record["start_term"] == "Fall"
    assert record["citizenship"] == "International"


def test_extract_date_added_variants():
    # The cleaner supports multiple date formats and skips placeholder dates.
    assert clean._extract_date_added("Added 01/02/2026") == "01/02/2026"
    assert clean._extract_date_added("Added Jan 2, 2026") == "Jan 2, 2026"
    assert clean._extract_date_added("Added 2 Jan 2026") == "2 Jan 2026"
    assert clean._extract_date_added("31/12/1969") is None


def test_extract_notes_and_degree_type_missing():
    # When Notes or Degree blocks are missing, helpers should return None.
    assert clean._extract_notes("No notes here") is None
    assert clean._extract_degree_type("Program Computer Science") is None


def test_gpa_extraction_edge_cases():
    # _extract_gpa should ignore NONE/0 and return None.
    assert clean._extract_gpa("Undergrad GPA: NONE GRE General: 165") is None
    assert clean._extract_gpa("Undergrad GPA: 0 GRE General: 165") is None


def test_none_if_zero_and_sanitize_text():
    # _none_if_zero should return None for numeric zero values.
    assert clean._none_if_zero("0") is None
    assert clean._none_if_zero(0) is None
    assert clean._none_if_zero("3.5") == "3.5"
    # Non-numeric values should be returned as-is (ValueError path).
    assert clean._none_if_zero("abc") == "abc"
    # None should pass through to None.
    assert clean._none_if_zero(None) is None

    # _sanitize_text should strip non-ASCII characters and collapse whitespace.
    assert clean._sanitize_text("Hello 🌟 world") == "Hello world"
    assert clean._sanitize_text("   ") is None
    # Passing None should short-circuit to None.
    assert clean._sanitize_text(None) is None


def test_save_and_load_data_roundtrip(tmp_path):
    # save_data/load_data should persist and restore JSON content.
    payload = [{"a": 1}]
    path = tmp_path / "data.json"
    clean.save_data(payload, str(path))
    assert clean.load_data(str(path)) == payload


def test_extract_helpers_return_none_when_missing():
    # _extract_date_added should return None when no date is found.
    assert clean._extract_date_added("No dates here") is None
    # _extract_gpa should return None when the pattern is missing.
    assert clean._extract_gpa("Undergrad GPA missing GRE General") is None
    # _normalize_decision should return None for unrecognized statuses.
    assert clean._normalize_decision("pending review") is None
