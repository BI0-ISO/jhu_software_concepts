"""
Unit tests for the pull pipeline (M2_material/pull_data.py).

These cover helper functions plus a few controlled paths through main().
"""

import json
import types
import builtins
from pathlib import Path

import pytest
import psycopg

from M2_material import pull_data
from db.db_config import get_db_config
from db.migrate import migrate

pytestmark = pytest.mark.db


@pytest.fixture()
def pull_paths(monkeypatch, tmp_path):
    # Redirect file outputs to a temporary directory.
    monkeypatch.setattr(pull_data, "DB_DIR", str(tmp_path))
    monkeypatch.setattr(pull_data, "STATE_PATH", str(tmp_path / "last_scraped_id.txt"))
    monkeypatch.setattr(pull_data, "DATA_PATH", str(tmp_path / "data.jsonl"))
    monkeypatch.setattr(pull_data, "LAST_ENTRIES_PATH", str(tmp_path / "last_entries.json"))
    monkeypatch.setattr(pull_data, "DONE_PATH", str(tmp_path / "pull.done"))
    monkeypatch.setattr(pull_data, "LATEST_SURVEY_PATH", str(tmp_path / "latest_survey_id.txt"))
    monkeypatch.setattr(pull_data, "PROGRESS_PATH", str(tmp_path / "progress.json"))
    return tmp_path


def test_extract_entry_id():
    assert pull_data._extract_entry_id("https://www.thegradcafe.com/result/123") == 123
    assert pull_data._extract_entry_id("bad") is None
    assert pull_data._extract_entry_id(None) is None


def test_read_write_last_scraped_id(pull_paths):
    # Missing file should return None.
    assert pull_data._read_last_scraped_id() is None

    # Write and read back the last scraped id.
    pull_data._write_last_scraped_id(42)
    assert pull_data._read_last_scraped_id() == 42

    # Invalid content should return None.
    (pull_paths / "last_scraped_id.txt").write_text("bad")
    assert pull_data._read_last_scraped_id() is None


def test_infer_last_id_from_file(pull_paths):
    # Build a JSONL file with multiple entries.
    data = [
        {"url": "https://www.thegradcafe.com/result/10"},
        {"url": "https://www.thegradcafe.com/result/20"},
    ]
    (pull_paths / "data.jsonl").write_text("\n".join(json.dumps(row) for row in data))
    assert pull_data._infer_last_id_from_file() == 20


def test_infer_last_id_from_file_missing_and_invalid(tmp_path, monkeypatch):
    # Missing file should return None.
    monkeypatch.setattr(pull_data, "DATA_PATH", str(tmp_path / "missing.jsonl"))
    assert pull_data._infer_last_id_from_file() is None

    # Invalid JSON and blank lines should be skipped.
    path = tmp_path / "data.jsonl"
    path.write_text("not json\n\n" + json.dumps({"url": "https://www.thegradcafe.com/result/5"}) + "\n")
    monkeypatch.setattr(pull_data, "DATA_PATH", str(path))
    assert pull_data._infer_last_id_from_file() == 5


def test_infer_last_id_from_file_oserror(tmp_path, monkeypatch):
    # If reading the file fails, return None.
    path = tmp_path / "data.jsonl"
    path.write_text(json.dumps({"url": "https://www.thegradcafe.com/result/10"}))
    monkeypatch.setattr(pull_data, "DATA_PATH", str(path))
    monkeypatch.setattr(builtins, "open", lambda *a, **k: (_ for _ in ()).throw(OSError("fail")))
    assert pull_data._infer_last_id_from_file() is None


def test_get_max_entry_id_from_db():
    # Ensure the table exists and insert a record for lookup.
    migrate()
    with psycopg.connect(**get_db_config(), autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE applicants RESTART IDENTITY")
            cur.execute(
                "INSERT INTO applicants (url) VALUES (%s)",
                ("https://www.thegradcafe.com/result/555",),
            )
            assert pull_data._get_max_entry_id_from_db(conn) == 555


def test_get_max_entry_id_from_db_error():
    # If the cursor fails, _get_max_entry_id_from_db should return None.
    class BadConn:
        def cursor(self):
            raise RuntimeError("boom")

    assert pull_data._get_max_entry_id_from_db(BadConn()) is None


def test_insert_new_records_and_url_exists():
    migrate()
    record = {
        "program": "Test",
        "comments": "c",
        "date_added": "2026-01-01",
        "acceptance_date": "2026-01-02",
        "url": "https://www.thegradcafe.com/result/777",
        "status": "accepted",
        "term": "Fall",
        "us_or_international": "American",
        "gpa": 3.5,
        "gre": 160,
        "gre_v": 150,
        "gre_aw": 4.0,
        "degree": "Masters",
        "llm_generated_program": "CS",
        "llm_generated_university": "Test",
    }

    with psycopg.connect(**get_db_config(), autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE applicants RESTART IDENTITY")
        inserted, duplicates = pull_data.insert_new_records(conn, [record])
        assert inserted == 1
        assert duplicates == 0
        assert pull_data.url_exists(conn, record["url"]) is True

        inserted, duplicates = pull_data.insert_new_records(conn, [record])
        assert inserted == 0
        assert duplicates == 1


def test_ensure_table_calls_migrate(monkeypatch):
    # ensure_table should call migrate().
    called = {"count": 0}
    monkeypatch.setattr(pull_data, "migrate", lambda: called.update(count=called["count"] + 1))
    pull_data.ensure_table(None)
    assert called["count"] == 1


def test_url_exists_none():
    # None URLs should return False without querying.
    assert pull_data.url_exists(None, None) is False


def test_write_last_entries(pull_paths):
    migrate()
    with psycopg.connect(**get_db_config(), autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE applicants RESTART IDENTITY")
            cur.execute(
                "INSERT INTO applicants (url) VALUES (%s)",
                ("https://www.thegradcafe.com/result/888",),
            )
        pull_data.write_last_entries(conn, pull_data.LAST_ENTRIES_PATH, limit=1)

    assert (pull_paths / "last_entries.json").exists()


def test_write_progress_and_log_event(pull_paths, capsys):
    pull_data._write_progress("running", 1, 0, 2, 10, started_at=0, last_attempted=5)
    data = json.loads((pull_paths / "progress.json").read_text())
    assert data["status"] == "running"

    pull_data._log_event("test_event", foo="bar")
    out = capsys.readouterr().out
    assert "test_event" in out


def test_write_progress_oserror(monkeypatch):
    # If writing progress fails, errors should be swallowed.
    monkeypatch.setattr(pull_data.os, "makedirs", lambda *a, **k: (_ for _ in ()).throw(OSError("fail")))
    pull_data._write_progress("running", 0, 0, 0, 1, started_at=0)


def test_log_event_fallback(monkeypatch, capsys):
    # If JSON serialization fails, fallback logging should be used.
    monkeypatch.setattr(pull_data.json, "dumps", lambda *_: (_ for _ in ()).throw(ValueError("bad")))
    pull_data._log_event("fallback_event", obj=object())
    out = capsys.readouterr().out
    assert "fallback_event" in out


def test_pull_job_init_and_update():
    migrate()
    with psycopg.connect(**get_db_config(), autocommit=True) as conn:
        job_id = pull_data._init_pull_job(conn, target=3)
        pull_data._update_pull_job(conn, job_id, "done", 1, 0, 2, last_attempted=999, error=None)

        with conn.cursor() as cur:
            cur.execute("SELECT status, inserted, processed FROM pull_jobs WHERE id = %s", (job_id,))
            row = cur.fetchone()
            assert row[0] == "done"
            assert row[1] == 1
            assert row[2] == 2


def test_standardize_with_llm_batch_success(monkeypatch):
    # Force LLM availability and stub urlopen response.
    monkeypatch.setattr(pull_data, "USE_LLM", True)
    monkeypatch.setattr(pull_data, "_LLM_AVAILABLE", True)

    class Resp:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return json.dumps({
                "rows": [
                    {"llm_generated_program": "CS", "llm_generated_university": "Test"},
                    {"llm_generated_program": "Math", "llm_generated_university": "Test2"},
                ]
            }).encode("utf-8")

    monkeypatch.setattr(pull_data.urllib.request, "urlopen", lambda *a, **k: Resp())

    rows = [{"program": "CS", "university": "Test"}, {"program": "Math", "university": "Test2"}]
    out = pull_data._standardize_with_llm_batch(rows)
    assert out[0]["llm_generated_program"] == "CS"


def test_standardize_with_llm_batch_recurses_on_error(monkeypatch):
    # Simulate a failure on first call, then success for smaller batches.
    monkeypatch.setattr(pull_data, "USE_LLM", True)
    monkeypatch.setattr(pull_data, "_LLM_AVAILABLE", True)
    calls = {"count": 0}

    class Resp:
        def __init__(self, rows):
            self._rows = rows

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return json.dumps({"rows": self._rows}).encode("utf-8")

    def fake_urlopen(req, timeout=None):
        calls["count"] += 1
        if calls["count"] == 1:
            raise pull_data.urllib.error.URLError("fail")
        return Resp([{"llm_generated_program": "CS", "llm_generated_university": "Test"}])

    monkeypatch.setattr(pull_data.urllib.request, "urlopen", fake_urlopen)

    rows = [{"program": "CS", "university": "Test"}, {"program": "Math", "university": "Test2"}]
    out = pull_data._standardize_with_llm_batch(rows)
    assert len(out) == 2


def test_standardize_requires_llm(monkeypatch):
    monkeypatch.setattr(pull_data, "USE_LLM", False)
    with pytest.raises(RuntimeError):
        pull_data._standardize_with_llm_batch([{ "program": "CS", "university": "Test" }])


def test_standardize_availability_failure(monkeypatch):
    # If the availability check fails, a RuntimeError should be raised.
    monkeypatch.setattr(pull_data, "USE_LLM", True)
    monkeypatch.setattr(pull_data, "_LLM_AVAILABLE", None)
    monkeypatch.setattr(pull_data, "_LLM_WARNED", False)

    def _raise(*args, **kwargs):
        raise pull_data.urllib.error.URLError("down")

    monkeypatch.setattr(pull_data.urllib.request, "urlopen", _raise)

    with pytest.raises(RuntimeError):
        pull_data._standardize_with_llm_batch([{"program": "CS", "university": "Test"}])


def test_standardize_len_mismatch_single_row(monkeypatch):
    # A length mismatch should raise a RuntimeError for a single row.
    monkeypatch.setattr(pull_data, "USE_LLM", True)
    monkeypatch.setattr(pull_data, "_LLM_AVAILABLE", True)

    class Resp:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return json.dumps({"rows": []}).encode("utf-8")

    monkeypatch.setattr(pull_data.urllib.request, "urlopen", lambda *a, **k: Resp())

    with pytest.raises(RuntimeError):
        pull_data._standardize_with_llm_batch([{"program": "CS", "university": "Test"}])


def test_main_no_new_entries(monkeypatch, pull_paths):
    # Simulate last_id >= latest_id so the pull exits early.
    monkeypatch.setattr(pull_data, "_get_max_entry_id_from_db", lambda conn: 10)
    monkeypatch.setattr(pull_data, "get_latest_survey_id", lambda: 10)
    monkeypatch.setattr(pull_data, "ensure_table", lambda conn: None)
    monkeypatch.setattr(pull_data, "write_last_entries", lambda *a, **k: None)

    class DummyConn:
        def close(self):
            pass

    monkeypatch.setattr(pull_data.psycopg, "connect", lambda **kwargs: DummyConn())
    # Ensure argparse doesn't try to parse pytest args.
    monkeypatch.setattr(pull_data.sys, "argv", ["pull_data.py"])

    pull_data.main()
    done = json.loads((pull_paths / "pull.done").read_text())
    assert done["status"] == "no_new_entries"


def test_main_timeout_no_pages(monkeypatch, pull_paths):
    # Simulate no pages and a timeout stop reason.
    monkeypatch.setattr(pull_data, "_get_max_entry_id_from_db", lambda conn: None)
    monkeypatch.setattr(pull_data, "_read_last_scraped_id", lambda: None)
    monkeypatch.setattr(pull_data, "_infer_last_id_from_file", lambda: None)
    monkeypatch.setattr(pull_data, "get_latest_survey_id", lambda: None)
    monkeypatch.setattr(pull_data, "scrape_data", lambda *a, **k: iter([]))
    monkeypatch.setattr(pull_data, "get_last_stop_reason", lambda: "timeout")
    monkeypatch.setattr(pull_data, "get_last_attempted_id", lambda: 999)
    monkeypatch.setattr(pull_data, "_write_last_scraped_id", lambda v: None)
    monkeypatch.setattr(pull_data, "_write_progress", lambda *a, **k: None)
    monkeypatch.setattr(pull_data, "_init_pull_job", lambda *a, **k: 1)
    monkeypatch.setattr(pull_data, "_update_pull_job", lambda *a, **k: None)
    monkeypatch.setattr(pull_data, "ensure_table", lambda conn: None)
    monkeypatch.setattr(pull_data, "write_last_entries", lambda *a, **k: None)

    class DummyConn:
        def close(self):
            pass

    monkeypatch.setattr(pull_data.psycopg, "connect", lambda **kwargs: DummyConn())
    # Ensure argparse doesn't try to parse pytest args.
    monkeypatch.setattr(pull_data.sys, "argv", ["pull_data.py"])

    pull_data.main()
    done = json.loads((pull_paths / "pull.done").read_text())
    assert done["status"] == "timeout"


def test_main_reaches_target(monkeypatch, pull_paths):
    # Simulate one page scraped and target reached.
    monkeypatch.setattr(pull_data, "_get_max_entry_id_from_db", lambda conn: 900)
    monkeypatch.setattr(pull_data, "get_latest_survey_id", lambda: 1000)
    monkeypatch.setattr(pull_data, "scrape_data", lambda *a, **k: iter([{"url": "https://www.thegradcafe.com/result/901", "html": "<div></div>", "date_added": "2026-01-01"}]))
    monkeypatch.setattr(pull_data, "clean_data", lambda pages: [{"url": pages[0]["url"], "program": "CS", "university": "Test"}])
    monkeypatch.setattr(pull_data, "url_exists", lambda conn, url: False)
    monkeypatch.setattr(pull_data, "_standardize_with_llm_batch", lambda rows: rows)
    monkeypatch.setattr(pull_data, "normalize_record", lambda r: {
        "program": "Test",
        "comments": "c",
        "date_added": "2026-01-01",
        "acceptance_date": "2026-01-02",
        "url": r["url"],
        "status": "accepted",
        "term": "Fall",
        "us_or_international": "American",
        "gpa": 3.5,
        "gre": 160,
        "gre_v": 150,
        "gre_aw": 4.0,
        "degree": "Masters",
        "llm_generated_program": "CS",
        "llm_generated_university": "Test",
    })
    monkeypatch.setattr(pull_data, "insert_new_records", lambda conn, records: (1, 0))
    monkeypatch.setattr(pull_data, "get_last_attempted_id", lambda: 901)
    monkeypatch.setattr(pull_data, "get_last_stop_reason", lambda: None)
    monkeypatch.setattr(pull_data, "_write_last_scraped_id", lambda v: None)
    monkeypatch.setattr(pull_data, "_write_progress", lambda *a, **k: None)
    monkeypatch.setattr(pull_data, "_init_pull_job", lambda *a, **k: 1)
    monkeypatch.setattr(pull_data, "_update_pull_job", lambda *a, **k: None)
    monkeypatch.setattr(pull_data, "ensure_table", lambda conn: None)
    monkeypatch.setattr(pull_data, "write_last_entries", lambda *a, **k: None)
    monkeypatch.setattr(pull_data, "TARGET_NEW_RECORDS", 1)
    monkeypatch.setattr(pull_data, "LLM_BATCH_SIZE", 1)

    class DummyConn:
        def close(self):
            pass

    monkeypatch.setattr(pull_data.psycopg, "connect", lambda **kwargs: DummyConn())
    # Ensure argparse doesn't try to parse pytest args.
    monkeypatch.setattr(pull_data.sys, "argv", ["pull_data.py"])

    pull_data.main()
    done = json.loads((pull_paths / "pull.done").read_text())
    assert done["status"] == "target_reached"


def test_main_handles_exception(monkeypatch, pull_paths):
    # Force an exception so the error handler sets status=error.
    def _raise(**kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(pull_data.psycopg, "connect", _raise)
    # Ensure argparse doesn't try to parse pytest args.
    monkeypatch.setattr(pull_data.sys, "argv", ["pull_data.py"])

    pull_data.main()
    done = json.loads((pull_paths / "pull.done").read_text())
    assert done["status"] == "error"


def test_standardize_initial_availability_check(monkeypatch):
    # Cover the branch where _LLM_AVAILABLE starts as None.
    monkeypatch.setattr(pull_data, "USE_LLM", True)
    monkeypatch.setattr(pull_data, "_LLM_AVAILABLE", None)
    monkeypatch.setattr(pull_data, "_LLM_WARNED", False)

    calls = {"count": 0}

    class Resp:
        def __init__(self, payload):
            self._payload = payload

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return json.dumps(self._payload).encode("utf-8")

    def fake_urlopen(req, timeout=None):
        calls["count"] += 1
        if calls["count"] == 1:
            # Availability check (payload content ignored).
            return Resp({"rows": []})
        return Resp({"rows": [{"llm_generated_program": "CS", "llm_generated_university": "Test"}]})

    monkeypatch.setattr(pull_data.urllib.request, "urlopen", fake_urlopen)

    rows = [{"program": "CS", "university": "Test"}]
    out = pull_data._standardize_with_llm_batch(rows)
    assert out[0]["llm_generated_program"] == "CS"


@pytest.mark.parametrize(
    "stop_reason, expected",
    [
        ("placeholder_streak", "no_more_entries"),
        ("error_streak", "fetch_failed"),
        (None, "no_new_data"),
    ],
)
def test_main_no_pages_status_variants(monkeypatch, pull_paths, stop_reason, expected):
    # When no pages are yielded, status should depend on stop_reason.
    monkeypatch.setattr(pull_data, "_get_max_entry_id_from_db", lambda conn: None)
    monkeypatch.setattr(pull_data, "_read_last_scraped_id", lambda: None)
    monkeypatch.setattr(pull_data, "_infer_last_id_from_file", lambda: None)
    monkeypatch.setattr(pull_data, "get_latest_survey_id", lambda: None)
    monkeypatch.setattr(pull_data, "scrape_data", lambda *a, **k: iter([]))
    monkeypatch.setattr(pull_data, "get_last_stop_reason", lambda: stop_reason)
    monkeypatch.setattr(pull_data, "get_last_attempted_id", lambda: 999)
    monkeypatch.setattr(pull_data, "_write_last_scraped_id", lambda v: None)
    monkeypatch.setattr(pull_data, "_write_progress", lambda *a, **k: None)
    monkeypatch.setattr(pull_data, "_init_pull_job", lambda *a, **k: 1)
    monkeypatch.setattr(pull_data, "_update_pull_job", lambda *a, **k: None)
    monkeypatch.setattr(pull_data, "ensure_table", lambda conn: None)
    monkeypatch.setattr(pull_data, "write_last_entries", lambda *a, **k: None)

    class DummyConn:
        def close(self):
            pass

    monkeypatch.setattr(pull_data.psycopg, "connect", lambda **kwargs: DummyConn())
    monkeypatch.setattr(pull_data.sys, "argv", ["pull_data.py"])

    pull_data.main()
    done = json.loads((pull_paths / "pull.done").read_text())
    assert done["status"] == expected


def test_main_success_with_duplicates_and_leftover_batch(monkeypatch, pull_paths):
    # Exercise duplicate handling, leftover batch insert, and success status.
    monkeypatch.setattr(pull_data, "_get_max_entry_id_from_db", lambda conn: 100)
    monkeypatch.setattr(pull_data, "get_latest_survey_id", lambda: 105)
    monkeypatch.setattr(pull_data, "scrape_data", lambda *a, **k: iter([
        {"url": "https://www.thegradcafe.com/result/101", "html": "<div></div>", "date_added": "2026-01-01"},
        {"url": "https://www.thegradcafe.com/result/102", "html": "<div></div>", "date_added": "2026-01-01"},
    ]))
    monkeypatch.setattr(pull_data, "clean_data", lambda pages: [{"url": pages[0]["url"], "program": "CS", "university": "Test"}])
    monkeypatch.setattr(pull_data, "url_exists", lambda conn, url: url.endswith("/101"))
    monkeypatch.setattr(pull_data, "_standardize_with_llm_batch", lambda rows: rows)
    monkeypatch.setattr(pull_data, "normalize_record", lambda r: r | {
        "comments": "c",
        "date_added": "2026-01-01",
        "acceptance_date": "2026-01-02",
        "status": "accepted",
        "term": "Fall",
        "us_or_international": "American",
        "gpa": 3.5,
        "gre": 160,
        "gre_v": 150,
        "gre_aw": 4.0,
        "degree": "Masters",
        "llm_generated_program": "CS",
        "llm_generated_university": "Test",
    })
    monkeypatch.setattr(pull_data, "insert_new_records", lambda conn, records: (1, 0))
    monkeypatch.setattr(pull_data, "get_last_attempted_id", lambda: 102)
    monkeypatch.setattr(pull_data, "get_last_stop_reason", lambda: None)
    monkeypatch.setattr(pull_data, "_write_last_scraped_id", lambda v: None)
    monkeypatch.setattr(pull_data, "_write_progress", lambda *a, **k: None)
    monkeypatch.setattr(pull_data, "_init_pull_job", lambda *a, **k: 1)
    monkeypatch.setattr(pull_data, "_update_pull_job", lambda *a, **k: None)
    monkeypatch.setattr(pull_data, "ensure_table", lambda conn: None)
    monkeypatch.setattr(pull_data, "write_last_entries", lambda *a, **k: None)
    monkeypatch.setattr(pull_data, "TARGET_NEW_RECORDS", 5)
    monkeypatch.setattr(pull_data, "LLM_BATCH_SIZE", 10)

    class DummyConn:
        def close(self):
            pass

    monkeypatch.setattr(pull_data.psycopg, "connect", lambda **kwargs: DummyConn())
    monkeypatch.setattr(pull_data.sys, "argv", ["pull_data.py"])

    pull_data.main()
    done = json.loads((pull_paths / "pull.done").read_text())
    assert done["status"] == "success"


def test_main_no_more_entries_after_placeholder_with_no_inserts(monkeypatch, pull_paths):
    # placeholder_streak after pages but no inserts should yield no_more_entries.
    monkeypatch.setattr(pull_data, "_get_max_entry_id_from_db", lambda conn: 100)
    monkeypatch.setattr(pull_data, "get_latest_survey_id", lambda: None)
    monkeypatch.setattr(pull_data, "scrape_data", lambda *a, **k: iter([
        {"url": "https://www.thegradcafe.com/result/101", "html": "<div></div>", "date_added": "2026-01-01"},
    ]))
    monkeypatch.setattr(pull_data, "clean_data", lambda pages: [{"url": pages[0]["url"], "program": "CS", "university": "Test"}])
    monkeypatch.setattr(pull_data, "url_exists", lambda conn, url: True)
    monkeypatch.setattr(pull_data, "get_last_attempted_id", lambda: 101)
    monkeypatch.setattr(pull_data, "get_last_stop_reason", lambda: "placeholder_streak")
    monkeypatch.setattr(pull_data, "_write_last_scraped_id", lambda v: None)
    monkeypatch.setattr(pull_data, "_write_progress", lambda *a, **k: None)
    monkeypatch.setattr(pull_data, "_init_pull_job", lambda *a, **k: 1)
    monkeypatch.setattr(pull_data, "_update_pull_job", lambda *a, **k: None)
    monkeypatch.setattr(pull_data, "ensure_table", lambda conn: None)
    monkeypatch.setattr(pull_data, "write_last_entries", lambda *a, **k: None)

    class DummyConn:
        def close(self):
            pass

    monkeypatch.setattr(pull_data.psycopg, "connect", lambda **kwargs: DummyConn())
    monkeypatch.setattr(pull_data.sys, "argv", ["pull_data.py"])

    pull_data.main()
    done = json.loads((pull_paths / "pull.done").read_text())
    assert done["status"] == "no_more_entries"


@pytest.mark.parametrize("stop_reason, expected", [("timeout", "timeout"), ("error_streak", "fetch_failed")])
def test_main_stop_reason_timeout_and_error(monkeypatch, pull_paths, stop_reason, expected):
    # When pages were seen and stop_reason is timeout/error_streak, set status accordingly.
    monkeypatch.setattr(pull_data, "_get_max_entry_id_from_db", lambda conn: 100)
    monkeypatch.setattr(pull_data, "get_latest_survey_id", lambda: None)
    monkeypatch.setattr(pull_data, "scrape_data", lambda *a, **k: iter([
        {"url": "https://www.thegradcafe.com/result/101", "html": "<div></div>", "date_added": "2026-01-01"},
    ]))
    monkeypatch.setattr(pull_data, "clean_data", lambda pages: [{"url": pages[0]["url"], "program": "CS", "university": "Test"}])
    monkeypatch.setattr(pull_data, "url_exists", lambda conn, url: True)
    monkeypatch.setattr(pull_data, "get_last_attempted_id", lambda: 101)
    monkeypatch.setattr(pull_data, "get_last_stop_reason", lambda: stop_reason)
    monkeypatch.setattr(pull_data, "_write_last_scraped_id", lambda v: None)
    monkeypatch.setattr(pull_data, "_write_progress", lambda *a, **k: None)
    monkeypatch.setattr(pull_data, "_init_pull_job", lambda *a, **k: 1)
    monkeypatch.setattr(pull_data, "_update_pull_job", lambda *a, **k: None)
    monkeypatch.setattr(pull_data, "ensure_table", lambda conn: None)
    monkeypatch.setattr(pull_data, "write_last_entries", lambda *a, **k: None)

    class DummyConn:
        def close(self):
            pass

    monkeypatch.setattr(pull_data.psycopg, "connect", lambda **kwargs: DummyConn())
    monkeypatch.setattr(pull_data.sys, "argv", ["pull_data.py"])

    pull_data.main()
    done = json.loads((pull_paths / "pull.done").read_text())
    assert done["status"] == expected

def test_main_partial_new_entries_placeholder(monkeypatch, pull_paths):
    # Stop reason placeholder_streak with inserted records => partial_new_entries.
    monkeypatch.setattr(pull_data, "_get_max_entry_id_from_db", lambda conn: 100)
    monkeypatch.setattr(pull_data, "get_latest_survey_id", lambda: None)
    monkeypatch.setattr(pull_data, "scrape_data", lambda *a, **k: iter([
        {"url": "https://www.thegradcafe.com/result/101", "html": "<div></div>", "date_added": "2026-01-01"},
    ]))
    monkeypatch.setattr(pull_data, "clean_data", lambda pages: [{"url": pages[0]["url"], "program": "CS", "university": "Test"}])
    monkeypatch.setattr(pull_data, "url_exists", lambda conn, url: False)
    monkeypatch.setattr(pull_data, "_standardize_with_llm_batch", lambda rows: rows)
    monkeypatch.setattr(pull_data, "normalize_record", lambda r: r | {
        "comments": "c",
        "date_added": "2026-01-01",
        "acceptance_date": "2026-01-02",
        "status": "accepted",
        "term": "Fall",
        "us_or_international": "American",
        "gpa": 3.5,
        "gre": 160,
        "gre_v": 150,
        "gre_aw": 4.0,
        "degree": "Masters",
        "llm_generated_program": "CS",
        "llm_generated_university": "Test",
    })
    monkeypatch.setattr(pull_data, "insert_new_records", lambda conn, records: (1, 0))
    monkeypatch.setattr(pull_data, "get_last_attempted_id", lambda: 101)
    monkeypatch.setattr(pull_data, "get_last_stop_reason", lambda: "placeholder_streak")
    monkeypatch.setattr(pull_data, "_write_last_scraped_id", lambda v: None)
    monkeypatch.setattr(pull_data, "_write_progress", lambda *a, **k: None)
    monkeypatch.setattr(pull_data, "_init_pull_job", lambda *a, **k: 1)
    monkeypatch.setattr(pull_data, "_update_pull_job", lambda *a, **k: None)
    monkeypatch.setattr(pull_data, "ensure_table", lambda conn: None)
    monkeypatch.setattr(pull_data, "write_last_entries", lambda *a, **k: None)
    monkeypatch.setattr(pull_data, "TARGET_NEW_RECORDS", 5)
    monkeypatch.setattr(pull_data, "LLM_BATCH_SIZE", 1)

    class DummyConn:
        def close(self):
            pass

    monkeypatch.setattr(pull_data.psycopg, "connect", lambda **kwargs: DummyConn())
    monkeypatch.setattr(pull_data.sys, "argv", ["pull_data.py"])

    pull_data.main()
    done = json.loads((pull_paths / "pull.done").read_text())
    assert done["status"] == "partial_new_entries"


def test_main_latest_id_no_new_entries_after_loop(monkeypatch, pull_paths):
    # last_attempted >= latest_id with no inserts => no_new_entries.
    monkeypatch.setattr(pull_data, "_get_max_entry_id_from_db", lambda conn: 100)
    monkeypatch.setattr(pull_data, "get_latest_survey_id", lambda: 101)
    monkeypatch.setattr(pull_data, "scrape_data", lambda *a, **k: iter([
        {"url": "https://www.thegradcafe.com/result/101", "html": "<div></div>", "date_added": "2026-01-01"},
    ]))
    monkeypatch.setattr(pull_data, "clean_data", lambda pages: [{"url": pages[0]["url"], "program": "CS", "university": "Test"}])
    monkeypatch.setattr(pull_data, "url_exists", lambda conn, url: True)
    monkeypatch.setattr(pull_data, "get_last_attempted_id", lambda: 101)
    monkeypatch.setattr(pull_data, "get_last_stop_reason", lambda: None)
    monkeypatch.setattr(pull_data, "_write_last_scraped_id", lambda v: None)
    monkeypatch.setattr(pull_data, "_write_progress", lambda *a, **k: None)
    monkeypatch.setattr(pull_data, "_init_pull_job", lambda *a, **k: 1)
    monkeypatch.setattr(pull_data, "_update_pull_job", lambda *a, **k: None)
    monkeypatch.setattr(pull_data, "ensure_table", lambda conn: None)
    monkeypatch.setattr(pull_data, "write_last_entries", lambda *a, **k: None)

    class DummyConn:
        def close(self):
            pass

    monkeypatch.setattr(pull_data.psycopg, "connect", lambda **kwargs: DummyConn())
    monkeypatch.setattr(pull_data.sys, "argv", ["pull_data.py"])

    pull_data.main()
    done = json.loads((pull_paths / "pull.done").read_text())
    assert done["status"] == "no_new_entries"


def test_main_latest_id_partial_new_entries_after_loop(monkeypatch, pull_paths):
    # last_attempted >= latest_id with inserts => partial_new_entries.
    monkeypatch.setattr(pull_data, "_get_max_entry_id_from_db", lambda conn: 100)
    monkeypatch.setattr(pull_data, "get_latest_survey_id", lambda: 101)
    monkeypatch.setattr(pull_data, "scrape_data", lambda *a, **k: iter([
        {"url": "https://www.thegradcafe.com/result/101", "html": "<div></div>", "date_added": "2026-01-01"},
    ]))
    monkeypatch.setattr(pull_data, "clean_data", lambda pages: [{"url": pages[0]["url"], "program": "CS", "university": "Test"}])
    monkeypatch.setattr(pull_data, "url_exists", lambda conn, url: False)
    monkeypatch.setattr(pull_data, "_standardize_with_llm_batch", lambda rows: rows)
    monkeypatch.setattr(pull_data, "normalize_record", lambda r: r | {
        "comments": "c",
        "date_added": "2026-01-01",
        "acceptance_date": "2026-01-02",
        "status": "accepted",
        "term": "Fall",
        "us_or_international": "American",
        "gpa": 3.5,
        "gre": 160,
        "gre_v": 150,
        "gre_aw": 4.0,
        "degree": "Masters",
        "llm_generated_program": "CS",
        "llm_generated_university": "Test",
    })
    monkeypatch.setattr(pull_data, "insert_new_records", lambda conn, records: (1, 0))
    monkeypatch.setattr(pull_data, "get_last_attempted_id", lambda: 101)
    monkeypatch.setattr(pull_data, "get_last_stop_reason", lambda: None)
    monkeypatch.setattr(pull_data, "_write_last_scraped_id", lambda v: None)
    monkeypatch.setattr(pull_data, "_write_progress", lambda *a, **k: None)
    monkeypatch.setattr(pull_data, "_init_pull_job", lambda *a, **k: 1)
    monkeypatch.setattr(pull_data, "_update_pull_job", lambda *a, **k: None)
    monkeypatch.setattr(pull_data, "ensure_table", lambda conn: None)
    monkeypatch.setattr(pull_data, "write_last_entries", lambda *a, **k: None)
    monkeypatch.setattr(pull_data, "TARGET_NEW_RECORDS", 5)
    monkeypatch.setattr(pull_data, "LLM_BATCH_SIZE", 1)

    class DummyConn:
        def close(self):
            pass

    monkeypatch.setattr(pull_data.psycopg, "connect", lambda **kwargs: DummyConn())
    monkeypatch.setattr(pull_data.sys, "argv", ["pull_data.py"])

    pull_data.main()
    done = json.loads((pull_paths / "pull.done").read_text())
    assert done["status"] == "partial_new_entries"


def test_main_no_new_data_after_loop(monkeypatch, pull_paths):
    # Inserted_total == 0 with no stop_reason => no_new_data.
    monkeypatch.setattr(pull_data, "_get_max_entry_id_from_db", lambda conn: 100)
    monkeypatch.setattr(pull_data, "get_latest_survey_id", lambda: None)
    monkeypatch.setattr(pull_data, "scrape_data", lambda *a, **k: iter([
        {"url": "https://www.thegradcafe.com/result/101", "html": "<div></div>", "date_added": "2026-01-01"},
    ]))
    monkeypatch.setattr(pull_data, "clean_data", lambda pages: [{"url": pages[0]["url"], "program": "CS", "university": "Test"}])
    monkeypatch.setattr(pull_data, "url_exists", lambda conn, url: True)
    monkeypatch.setattr(pull_data, "get_last_attempted_id", lambda: 101)
    monkeypatch.setattr(pull_data, "get_last_stop_reason", lambda: None)
    monkeypatch.setattr(pull_data, "_write_last_scraped_id", lambda v: None)
    monkeypatch.setattr(pull_data, "_write_progress", lambda *a, **k: None)
    monkeypatch.setattr(pull_data, "_init_pull_job", lambda *a, **k: 1)
    monkeypatch.setattr(pull_data, "_update_pull_job", lambda *a, **k: None)
    monkeypatch.setattr(pull_data, "ensure_table", lambda conn: None)
    monkeypatch.setattr(pull_data, "write_last_entries", lambda *a, **k: None)

    class DummyConn:
        def close(self):
            pass

    monkeypatch.setattr(pull_data.psycopg, "connect", lambda **kwargs: DummyConn())
    monkeypatch.setattr(pull_data.sys, "argv", ["pull_data.py"])

    pull_data.main()
    done = json.loads((pull_paths / "pull.done").read_text())
    assert done["status"] == "no_new_data"


def test_main_lock_path_write_error(monkeypatch, pull_paths, tmp_path):
    # If the lock file cannot be written, the pull should proceed without it.
    lock_path = tmp_path / "pull.lock"

    monkeypatch.setattr(pull_data, "_get_max_entry_id_from_db", lambda conn: 10)
    monkeypatch.setattr(pull_data, "get_latest_survey_id", lambda: 10)
    monkeypatch.setattr(pull_data, "ensure_table", lambda conn: None)
    monkeypatch.setattr(pull_data, "write_last_entries", lambda *a, **k: None)

    class DummyConn:
        def close(self):
            pass

    monkeypatch.setattr(pull_data.psycopg, "connect", lambda **kwargs: DummyConn())

    real_open = builtins.open

    def _open(path, mode="r", *args, **kwargs):
        if str(path) == str(lock_path) and "w" in mode:
            raise OSError("lock write fail")
        return real_open(path, mode, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", _open)
    monkeypatch.setattr(pull_data.sys, "argv", ["pull_data.py", "--lock", str(lock_path)])

    pull_data.main()
    done = json.loads((pull_paths / "pull.done").read_text())
    assert done["status"] == "no_new_entries"


def test_main_finally_error_paths(monkeypatch, pull_paths, tmp_path):
    # Force errors in the finally block: DONE_PATH write, update job, lock remove, and conn close.
    monkeypatch.setattr(pull_data, "_get_max_entry_id_from_db", lambda conn: None)
    monkeypatch.setattr(pull_data, "_read_last_scraped_id", lambda: None)
    monkeypatch.setattr(pull_data, "_infer_last_id_from_file", lambda: None)
    monkeypatch.setattr(pull_data, "get_latest_survey_id", lambda: None)
    monkeypatch.setattr(pull_data, "scrape_data", lambda *a, **k: iter([]))
    monkeypatch.setattr(pull_data, "get_last_stop_reason", lambda: None)
    monkeypatch.setattr(pull_data, "get_last_attempted_id", lambda: None)
    monkeypatch.setattr(pull_data, "_write_progress", lambda *a, **k: None)
    monkeypatch.setattr(pull_data, "_init_pull_job", lambda *a, **k: 1)
    monkeypatch.setattr(pull_data, "_update_pull_job", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("update fail")))
    monkeypatch.setattr(pull_data, "ensure_table", lambda conn: None)
    monkeypatch.setattr(pull_data, "write_last_entries", lambda *a, **k: None)

    lock_path = tmp_path / "pull.lock"
    lock_path.write_text("123")

    class DummyConn:
        def close(self):
            raise RuntimeError("close fail")

    monkeypatch.setattr(pull_data.psycopg, "connect", lambda **kwargs: DummyConn())

    real_open = builtins.open

    def _open(path, mode="r", *args, **kwargs):
        if str(path) == str(pull_data.DONE_PATH) and "w" in mode:
            raise OSError("done write fail")
        return real_open(path, mode, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", _open)
    monkeypatch.setattr(pull_data.os, "remove", lambda *_: (_ for _ in ()).throw(OSError("remove fail")))
    monkeypatch.setattr(pull_data.sys, "argv", ["pull_data.py", "--lock", str(lock_path)])

    pull_data.main()


def test_pull_data_fallback_imports(monkeypatch):
    # Execute pull_data.py without package context to cover fallback imports.
    import runpy
    import types
    import sys

    fake_scrape = types.ModuleType("scrape")
    fake_scrape.scrape_data = lambda *a, **k: iter([])
    fake_scrape.get_last_stop_reason = lambda: None
    fake_scrape.get_last_attempted_id = lambda: None
    fake_scrape.get_latest_survey_id = lambda: None

    fake_clean = types.ModuleType("clean")
    fake_clean.clean_data = lambda pages: []

    monkeypatch.setitem(sys.modules, "scrape", fake_scrape)
    monkeypatch.setitem(sys.modules, "clean", fake_clean)

    root = Path(__file__).resolve().parents[1]
    runpy.run_path(str(root / "src" / "M2_material" / "pull_data.py"), run_name="pull_data_test")


def test_pull_data_script_entry(monkeypatch, tmp_path):
    # Run pull_data as a script to hit the __main__ entrypoint.
    import runpy
    import sys
    import config as cfg
    import psycopg
    import db.migrate as migrate_mod

    # Point DB_DIR/BASE_DIR to temp to avoid writing into the repo.
    monkeypatch.setattr(cfg, "DB_DIR", str(tmp_path))
    monkeypatch.setattr(cfg, "BASE_DIR", str(tmp_path))

    # Stub out network/data dependencies.
    fake_scrape = types.SimpleNamespace(
        scrape_data=lambda *a, **k: iter([]),
        get_last_stop_reason=lambda: None,
        get_last_attempted_id=lambda: None,
        get_latest_survey_id=lambda: None,
    )
    fake_clean = types.SimpleNamespace(clean_data=lambda pages: [])

    monkeypatch.setitem(sys.modules, "scrape", fake_scrape)
    monkeypatch.setitem(sys.modules, "clean", fake_clean)

    class DummyConn:
        def close(self):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(psycopg, "connect", lambda **kwargs: DummyConn())
    monkeypatch.setattr(migrate_mod, "migrate", lambda: None)

    monkeypatch.setattr(sys, "argv", ["pull_data.py"])
    root = Path(__file__).resolve().parents[1]
    runpy.run_path(str(root / "src" / "M2_material" / "pull_data.py"), run_name="__main__")
