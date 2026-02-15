"""
Unit tests for db.normalize helpers.

These cover parsing, formatting, and record normalization logic.
"""

import json

import pytest

from db import normalize

pytestmark = pytest.mark.db


def test_load_records_json_and_jsonl(tmp_path):
    # JSON array file.
    array_path = tmp_path / "data.json"
    data = [{"a": 1}, {"b": 2}]
    array_path.write_text(json.dumps(data))
    assert normalize.load_records(str(array_path)) == data

    # JSONL file.
    jsonl_path = tmp_path / "data.jsonl"
    jsonl_path.write_text("\n".join(json.dumps(row) for row in data) + "\n\n")
    assert normalize.load_records(str(jsonl_path)) == data

    # Empty file should return an empty list (no first non-space char).
    empty_path = tmp_path / "empty.jsonl"
    empty_path.write_text("")
    assert normalize.load_records(str(empty_path)) == []


def test_clean_text_and_extract_number(monkeypatch):
    # clean_text should strip whitespace and convert empty strings to None.
    assert normalize.clean_text("  hi \x00") == "hi"
    assert normalize.clean_text("   ") is None
    assert normalize.clean_text(None) is None

    # extract_number should find numeric tokens in strings.
    assert normalize.extract_number("1,234.5") == 1234.5
    assert normalize.extract_number("no digits") is None
    assert normalize.extract_number(7) == 7.0
    assert normalize.extract_number(None) is None

    # Force the ValueError branch by returning a non-numeric match.
    class DummyMatch:
        def group(self, *_):
            return "not-a-number"

    monkeypatch.setattr(normalize.re, "search", lambda *a, **k: DummyMatch())
    assert normalize.extract_number("123") is None


def test_parse_date_and_status_helpers():
    # parse_date should accept multiple formats.
    assert normalize.parse_date("2026-01-15") == "2026-01-15"
    assert normalize.parse_date("January 5, 2026") == "2026-01-05"
    assert normalize.parse_date("Jan 5, 2026") == "2026-01-05"
    # The parser tries %m/%d/%Y before %d/%m/%Y, so this becomes May 1st.
    assert normalize.parse_date("05/01/2026") == "2026-05-01"
    assert normalize.parse_date("") is None
    assert normalize.parse_date("   ") is None
    assert normalize.parse_date("not a date") is None

    # datetime/date objects should be converted.
    from datetime import datetime, date
    assert normalize.parse_date(datetime(2026, 1, 1)) == "2026-01-01"
    assert normalize.parse_date(date(2026, 1, 2)) == "2026-01-02"

    # normalize_status should map common labels.
    assert normalize.normalize_status("Accepted") == "accepted"
    assert normalize.normalize_status("Rejected") == "rejected"
    assert normalize.normalize_status("Waitlisted") == "waitlisted"
    assert normalize.normalize_status("Interview") == "interview"
    assert normalize.normalize_status("") is None
    assert normalize.normalize_status("Pending") == "pending"


def test_term_year_and_decision_date_helpers():
    assert normalize.term_from_semester_year("Fall 2026") == "Fall"
    assert normalize.term_from_semester_year(None) is None
    assert normalize.term_from_semester_year("   ") is None
    assert normalize.term_from_semester_year("123") is None

    assert normalize.extract_year("Fall 2026") == "2026"
    assert normalize.extract_year("") is None

    assert normalize.parse_decision_date("17 Jan", "2026") == "2026-01-17"
    assert normalize.parse_decision_date("17 Jan", None) is None
    assert normalize.parse_decision_date("bad", "2026") is None


def test_program_university_helpers():
    program, uni = normalize.split_program_university("Computer Science, Johns Hopkins University")
    assert program == "Computer Science"
    assert uni == "Johns Hopkins University"

    program, uni = normalize.split_program_university("Data Science, University")
    assert program == "Data Science"
    assert uni == "University"

    program, uni = normalize.split_program_university("Computer Science")
    assert program == "Computer Science"
    assert uni is None
    program, uni = normalize.split_program_university(None)
    assert program is None and uni is None

    assert normalize.format_program("Johns Hopkins University", "Computer Science") == "Johns Hopkins University, Computer Science"
    assert normalize.format_program(None, "Computer Science") == "Computer Science"
    assert normalize.format_program("Johns Hopkins University", None) == "Johns Hopkins University"


def test_normalize_record_and_records():
    raw = {
        "program": "Computer Science, Johns Hopkins University",
        "university": None,
        "comments": "hello",
        "date_added": "2026-01-05",
        "url": "https://www.thegradcafe.com/result/999300",
        "applicant_status": "Accepted",
        "acceptance_date": "Jan 6, 2026",
        "semester_year_start": None,
        "citizenship": "American",
        "gpa": "3.9",
        "gre_total": "160",
        "gre_verbal": "158",
        "gre_aw": "4.0",
        "degree_type": "Masters",
        "llm_generated_program": "Computer Science",
        "llm_generated_university": "Johns Hopkins University",
        "start_term": "Spring 2026",
        "decision_date": "17 Jan",
    }

    record = normalize.normalize_record(raw)
    assert record["program"] == "Johns Hopkins University, Computer Science"
    assert record["status"] == "accepted"
    assert record["term"] == "Spring"
    assert record["gpa"] == 3.9
    assert record["gre"] == 160.0

    # If acceptance_date is missing but status is accepted, decision_date should be parsed.
    raw_missing_acceptance = dict(raw)
    raw_missing_acceptance["acceptance_date"] = None
    raw_missing_acceptance["decision_date"] = "17 Jan"
    fallback_record = normalize.normalize_record(raw_missing_acceptance)
    assert fallback_record["acceptance_date"] == "2026-01-17"

    records = normalize.normalize_records([raw])
    assert isinstance(records, list)
    assert len(records) == 1
