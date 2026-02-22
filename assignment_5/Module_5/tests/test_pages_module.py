"""
Extensive tests for M3_material.board.pages helpers and routes.

These tests mock filesystem, network, and subprocess interactions to keep
execution fast and deterministic.
"""

import json
import time
import builtins

import pytest

from M3_material.board import pages

pytestmark = pytest.mark.web


@pytest.fixture()
def temp_paths(monkeypatch, tmp_path):
    # Redirect all file paths used by pages.py into a temp directory.
    monkeypatch.setattr(pages, "LOCK_PATH", str(tmp_path / "pull.lock"))
    monkeypatch.setattr(pages, "DONE_PATH", str(tmp_path / "pull.done"))
    monkeypatch.setattr(pages, "PROGRESS_PATH", str(tmp_path / "progress.json"))
    monkeypatch.setattr(pages, "LATEST_SURVEY_PATH", str(tmp_path / "latest_survey_id.txt"))
    monkeypatch.setattr(pages, "ANALYSIS_CACHE_PATH", str(tmp_path / "analysis_cache.json"))
    monkeypatch.setattr(pages, "REPORT_PATH", str(tmp_path / "report.pdf"))
    monkeypatch.setattr(pages, "LOG_PATH", str(tmp_path / "pull.log"))
    return tmp_path


@pytest.fixture(autouse=True)
def reset_pull_state():
    # Ensure global pull state is clean across tests.
    pages.PULL_PROCESS = None
    pages.PULL_LAST_EXIT = None
    yield
    pages.PULL_PROCESS = None
    pages.PULL_LAST_EXIT = None


def test_pid_running_true_false(monkeypatch):
    # Simulate a running PID with a no-op os.kill.
    monkeypatch.setattr(pages.os, "kill", lambda pid, sig: None)
    assert pages._pid_running(123) is True

    # Simulate a missing PID by raising OSError.
    def _raise(pid, sig):
        raise OSError("not running")

    monkeypatch.setattr(pages.os, "kill", _raise)
    assert pages._pid_running(123) is False


def test_llm_status_url_env_override(monkeypatch):
    # When LLM_HOST_URL is set, the status URL should be derived from it.
    monkeypatch.setenv("LLM_HOST_URL", "http://localhost:8000/standardize")
    assert pages._llm_status_url().endswith("/status")

    # When not set, fallback should use LLM_HOST/LLM_PORT.
    monkeypatch.delenv("LLM_HOST_URL", raising=False)
    assert pages._llm_status_url().startswith("http://")


def test_is_llm_ready_variants(monkeypatch):
    # Valid JSON with model_loaded True should return True.
    class Resp:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return json.dumps({"model_loaded": True}).encode("utf-8")

    monkeypatch.setattr(pages.urllib.request, "urlopen", lambda *a, **k: Resp())
    assert pages._is_llm_ready() is True

    # Non-2xx status should return False.
    class BadResp(Resp):
        status = 500

    monkeypatch.setattr(pages.urllib.request, "urlopen", lambda *a, **k: BadResp())
    assert pages._is_llm_ready() is False

    # Invalid JSON should return False.
    class BadJson(Resp):
        def read(self):
            return b"not json"

    monkeypatch.setattr(pages.urllib.request, "urlopen", lambda *a, **k: BadJson())
    assert pages._is_llm_ready() is False

    # Exceptions should return False.
    def _raise(*args, **kwargs):
        raise pages.urllib.error.URLError("boom")

    monkeypatch.setattr(pages.urllib.request, "urlopen", _raise)
    assert pages._is_llm_ready() is False


def test_cfg_and_paths(app):
    # Without app context, _cfg should return the default.
    assert pages._cfg("MISSING", "default") == "default"

    # With app context, config overrides should be returned.
    with app.app_context():
        app.config["ANALYSIS_CACHE_PATH"] = "/tmp/cache.json"
        app.config["REPORT_PATH"] = "/tmp/report.pdf"
        assert pages._analysis_cache_path() == "/tmp/cache.json"
        assert pages._report_path() == "/tmp/report.pdf"


def test_compute_results_seeds_base_dataset(app, monkeypatch):
    # When not in TESTING mode, _compute_results should seed the base dataset.
    called = {"count": 0}
    monkeypatch.setattr(pages, "seed_base_dataset", lambda: called.update(count=called["count"] + 1))
    app.config["TESTING"] = False
    app.config["COMPUTE_RESULTS"] = lambda: {"year_2026": {}, "all_time": {}, "total_applicants": 0}

    with app.app_context():
        result = pages._compute_results()

    assert called["count"] == 1
    assert "year_2026" in result


def test_cache_helpers(temp_paths):
    # Write results to cache and read them back.
    results = {"year_2026": {}, "all_time": {}, "total_applicants": 1}
    pages._write_cached_results(results)
    cached = pages._read_cached_results()
    assert cached["total_applicants"] == 1
    assert "_meta" in cached

    # Invalid JSON should return None.
    bad_path = temp_paths / "analysis_cache.json"
    bad_path.write_text("not json")
    assert pages._read_cached_results() is None


def test_read_progress_and_latest_survey(temp_paths):
    # Progress file should load JSON when present.
    progress_path = temp_paths / "progress.json"
    progress_path.write_text(json.dumps({"processed": 1}))
    assert pages._read_progress()["processed"] == 1

    # Invalid JSON should yield None.
    progress_path.write_text("bad")
    assert pages._read_progress() is None

    # Latest survey ID parsing.
    latest_path = temp_paths / "latest_survey_id.txt"
    latest_path.write_text("123")
    assert pages._read_latest_survey_id() == 123

    latest_path.write_text("bad")
    assert pages._read_latest_survey_id() is None

    # No latest survey file should return None (missing file branch).
    latest_path.unlink()
    assert pages._read_latest_survey_id() is None


def test_read_cached_results_invalid_shapes(temp_paths):
    # Non-dict JSON should return None.
    cache_path = temp_paths / "analysis_cache.json"
    cache_path.write_text(json.dumps([1, 2, 3]))
    assert pages._read_cached_results() is None

    # Dict missing required keys should return None.
    cache_path.write_text(json.dumps({"year_2026": {}}))
    assert pages._read_cached_results() is None


def test_read_last_pull_job_db(app):
    # Insert a pull_jobs row and verify it is returned by _read_last_pull_job.
    from db.db_config import get_db_config
    import psycopg

    with psycopg.connect(**get_db_config(), autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO pull_jobs (status, inserted, processed) VALUES (%s, %s, %s)",
                ("running", 1, 2),
            )

    job = pages._read_last_pull_job()
    assert job is not None
    assert job["status"] == "running"


def test_read_last_pull_job_handles_error(monkeypatch):
    # Force psycopg.connect to raise to hit the exception branch.
    monkeypatch.setattr(pages.psycopg, "connect", lambda **k: (_ for _ in ()).throw(RuntimeError("fail")))
    assert pages._read_last_pull_job() is None


def test_is_pull_running_done_and_empty_lock(temp_paths):
    # DONE_PATH present should clear the lock and return False.
    lock_path = temp_paths / "pull.lock"
    done_path = temp_paths / "pull.done"
    lock_path.write_text("123")
    done_path.write_text("done")

    assert pages._is_pull_running() is False
    assert not lock_path.exists()

    # Empty lock file should be removed and treated as not running.
    lock_path.write_text("")
    assert pages._is_pull_running() is False
    assert not lock_path.exists()


def test_is_pull_running_done_remove_error(temp_paths, monkeypatch):
    # If LOCK_PATH removal fails, _is_pull_running should still return False.
    (temp_paths / "pull.done").write_text("done")
    (temp_paths / "pull.lock").write_text("123")

    def _raise(path):
        raise OSError("nope")

    monkeypatch.setattr(pages.os, "remove", _raise)
    assert pages._is_pull_running() is False


def test_is_pull_running_starting_age(temp_paths, monkeypatch):
    # "starting" lock should be considered running if recent, otherwise removed.
    lock_path = temp_paths / "pull.lock"
    lock_path.write_text("starting")

    # Recent lock => running True.
    monkeypatch.setattr(pages.os.path, "getmtime", lambda p: time.time())
    assert pages._is_pull_running() is True

    # Old lock => removed and False.
    monkeypatch.setattr(pages.os.path, "getmtime", lambda p: time.time() - 20)
    assert pages._is_pull_running() is False
    assert not lock_path.exists()


def test_is_pull_running_pid_and_stale(temp_paths, monkeypatch):
    # PID lock with non-running process should be removed.
    lock_path = temp_paths / "pull.lock"
    lock_path.write_text("123")
    monkeypatch.setattr(pages, "_pid_running", lambda pid: False)
    assert pages._is_pull_running() is False
    assert not lock_path.exists()

    # PID lock with running process but stale timestamp should be removed.
    lock_path.write_text("123")
    monkeypatch.setattr(pages, "_pid_running", lambda pid: True)
    monkeypatch.setattr(pages.os.path, "getmtime", lambda p: time.time() - (pages.LOCK_STALE_SECONDS + 1))
    assert pages._is_pull_running() is False
    assert not lock_path.exists()

    # Recent PID lock should be considered running.
    lock_path.write_text("123")
    monkeypatch.setattr(pages.os.path, "getmtime", lambda p: time.time())
    assert pages._is_pull_running() is True


def test_is_pull_running_empty_lock(temp_paths):
    # Empty lock content should be removed and return False.
    lock_path = temp_paths / "pull.lock"
    lock_path.write_text("")
    assert pages._is_pull_running() is False
    assert not lock_path.exists()


def test_is_pull_running_no_files(temp_paths):
    # No DONE or LOCK files should return False (line 235).
    assert not (temp_paths / "pull.done").exists()
    assert not (temp_paths / "pull.lock").exists()
    assert pages._is_pull_running() is False


def test_is_pull_running_lock_read_error(temp_paths, monkeypatch):
    # If reading the lock file raises OSError, the function should proceed.
    lock_path = temp_paths / "pull.lock"
    lock_path.write_text("123")

    def _raise(*args, **kwargs):
        raise OSError("boom")

    monkeypatch.setattr(builtins, "open", _raise)
    # Also force getmtime to raise to hit the return True branch.
    monkeypatch.setattr(pages.os.path, "getmtime", lambda p: (_ for _ in ()).throw(OSError("fail")))
    assert pages._is_pull_running() is True


def test_is_pull_running_stale_remove_error(temp_paths, monkeypatch):
    # If stale lock removal fails, return False anyway.
    lock_path = temp_paths / "pull.lock"
    lock_path.write_text("123")
    monkeypatch.setattr(pages.os.path, "getmtime", lambda p: time.time() - (pages.LOCK_STALE_SECONDS + 1))

    def _raise(path):
        raise OSError("fail")

    monkeypatch.setattr(pages.os, "remove", _raise)
    assert pages._is_pull_running() is False


def test_is_pull_running_process_poll(monkeypatch):
    # If a process is running (poll() is None), return True.
    class DummyProc:
        def poll(self):
            return None

    pages.PULL_PROCESS = DummyProc()
    assert pages._is_pull_running() is True

    # If process finished, PULL_LAST_EXIT should be set and return False.
    class DoneProc:
        returncode = 0

        def poll(self):
            return 0

    pages.PULL_PROCESS = DoneProc()
    assert pages._is_pull_running() is False
    assert pages.PULL_LAST_EXIT == 0


def test_clear_pull_state_removes_files(temp_paths):
    # Create fake running process that fails terminate -> kill.
    calls = {"killed": 0}

    class DummyProc:
        def poll(self):
            return None

        def terminate(self):
            raise RuntimeError("fail terminate")

        def wait(self, timeout=None):
            raise RuntimeError("fail wait")

        def kill(self):
            calls["killed"] += 1

    pages.PULL_PROCESS = DummyProc()

    # Create lock/progress/done files to verify cleanup.
    (temp_paths / "pull.lock").write_text("123")
    (temp_paths / "pull.done").write_text("done")
    (temp_paths / "progress.json").write_text("{}")

    pages._clear_pull_state()

    assert calls["killed"] == 1
    assert not (temp_paths / "pull.lock").exists()
    assert not (temp_paths / "pull.done").exists()
    assert not (temp_paths / "progress.json").exists()


def test_clear_pull_state_success_path(temp_paths, monkeypatch):
    # When terminate/wait succeed, no kill should occur.
    calls = {"killed": 0}

    class DummyProc:
        def poll(self):
            return None

        def terminate(self):
            pass

        def wait(self, timeout=None):
            pass

        def kill(self):
            calls["killed"] += 1

    pages.PULL_PROCESS = DummyProc()

    # Force os.remove to raise to cover the OSError branch in cleanup.
    monkeypatch.setattr(pages.os, "remove", lambda p: (_ for _ in ()).throw(OSError("fail")))
    (temp_paths / "pull.lock").write_text("123")
    pages._clear_pull_state()
    assert calls["killed"] == 0


def test_clear_pull_state_kill_failure(monkeypatch):
    # If kill itself fails, the exception should be swallowed.
    class DummyProc:
        def poll(self):
            return None

        def terminate(self):
            raise RuntimeError("boom")

        def wait(self, timeout=None):
            raise RuntimeError("boom")

        def kill(self):
            raise RuntimeError("kill failed")

    pages.PULL_PROCESS = DummyProc()
    pages._clear_pull_state()


def test_start_pull_success_and_failure(temp_paths, monkeypatch):
    # Successful path should create a lock file with PID and return True.
    monkeypatch.setattr(pages, "_pull_running", lambda: False)
    monkeypatch.setattr(pages, "_llm_ready", lambda: True)

    class DummyProc:
        def __init__(self):
            self.pid = 999

        def poll(self):
            return None

    monkeypatch.setattr(pages.subprocess, "Popen", lambda *a, **k: DummyProc())

    assert pages._start_pull() is True
    assert (temp_paths / "pull.lock").read_text().strip() == "999"

    # Failure path should remove the lock and return False.
    (temp_paths / "pull.lock").write_text("starting")
    monkeypatch.setattr(pages.subprocess, "Popen", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    assert pages._start_pull() is False
    assert not (temp_paths / "pull.lock").exists()


def test_start_pull_busy_or_llm_not_ready(monkeypatch):
    # If a pull is already running, start should return False.
    monkeypatch.setattr(pages, "_pull_running", lambda: True)
    assert pages._start_pull() is False

    # If LLM not ready, start should return False.
    monkeypatch.setattr(pages, "_pull_running", lambda: False)
    monkeypatch.setattr(pages, "_llm_ready", lambda: False)
    assert pages._start_pull() is False


def test_start_pull_lock_write_error(monkeypatch, tmp_path):
    # Cover the lock write OSError branch.
    monkeypatch.setattr(pages, "_pull_running", lambda: False)
    monkeypatch.setattr(pages, "_llm_ready", lambda: True)

    log_dir = tmp_path / "logs"
    lock_dir = tmp_path / "locks"
    monkeypatch.setattr(pages, "LOG_PATH", str(log_dir / "pull.log"))
    monkeypatch.setattr(pages, "LOCK_PATH", str(lock_dir / "pull.lock"))

    real_makedirs = pages.os.makedirs

    def _makedirs(path, exist_ok=False):
        # Raise only for the lock directory to hit the except OSError branch.
        if path == str(lock_dir):
            raise OSError("fail")
        return real_makedirs(path, exist_ok=exist_ok)

    monkeypatch.setattr(pages.os, "makedirs", _makedirs)

    class DummyProc:
        def __init__(self):
            self.pid = 111

        def poll(self):
            return None

    monkeypatch.setattr(pages.subprocess, "Popen", lambda *a, **k: DummyProc())

    # Even with a lock write error, the function should continue and start.
    assert pages._start_pull() is True


def test_start_pull_pid_write_error(monkeypatch, tmp_path):
    # If writing the PID into the lock fails, the error should be swallowed.
    monkeypatch.setattr(pages, "_pull_running", lambda: False)
    monkeypatch.setattr(pages, "_llm_ready", lambda: True)

    log_dir = tmp_path / "logs"
    lock_dir = tmp_path / "locks"
    monkeypatch.setattr(pages, "LOG_PATH", str(log_dir / "pull.log"))
    monkeypatch.setattr(pages, "LOCK_PATH", str(lock_dir / "pull.lock"))

    class DummyProc:
        def __init__(self):
            self.pid = 222

        def poll(self):
            return None

    monkeypatch.setattr(pages.subprocess, "Popen", lambda *a, **k: DummyProc())

    real_open = builtins.open
    lock_writes = {"count": 0}

    def _open(path, mode="r", *args, **kwargs):
        if path == pages.LOCK_PATH and "w" in mode:
            lock_writes["count"] += 1
            if lock_writes["count"] > 1:
                raise OSError("fail pid write")
        return real_open(path, mode, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", _open)
    assert pages._start_pull() is True


def test_start_pull_log_write_error(monkeypatch, tmp_path):
    # If log_file.write fails, the exception path should be swallowed.
    monkeypatch.setattr(pages, "_pull_running", lambda: False)
    monkeypatch.setattr(pages, "_llm_ready", lambda: True)

    log_dir = tmp_path / "logs"
    lock_dir = tmp_path / "locks"
    monkeypatch.setattr(pages, "LOG_PATH", str(log_dir / "pull.log"))
    monkeypatch.setattr(pages, "LOCK_PATH", str(lock_dir / "pull.lock"))

    class DummyProc:
        def __init__(self):
            self.pid = 333

        def poll(self):
            return None

    def _raise(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(pages.subprocess, "Popen", _raise)

    class BadLog:
        def write(self, _):
            raise RuntimeError("fail write")

        def close(self):
            pass

    real_open = builtins.open

    def _open(path, mode="r", *args, **kwargs):
        if path == pages.LOG_PATH and "a" in mode:
            return BadLog()
        return real_open(path, mode, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", _open)
    assert pages._start_pull() is False


def test_start_pull_remove_lock_error(monkeypatch, tmp_path):
    # If removing the lock fails in the exception branch, it should be swallowed.
    monkeypatch.setattr(pages, "_pull_running", lambda: False)
    monkeypatch.setattr(pages, "_llm_ready", lambda: True)

    log_dir = tmp_path / "logs"
    lock_dir = tmp_path / "locks"
    monkeypatch.setattr(pages, "LOG_PATH", str(log_dir / "pull.log"))
    monkeypatch.setattr(pages, "LOCK_PATH", str(lock_dir / "pull.lock"))

    def _raise(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(pages.subprocess, "Popen", _raise)
    monkeypatch.setattr(pages.os, "remove", lambda *_: (_ for _ in ()).throw(OSError("fail")))

    # Create a lock file so the removal branch is exercised.
    lock_dir.mkdir(parents=True, exist_ok=True)
    (lock_dir / "pull.lock").write_text("starting")

    assert pages._start_pull() is False


def test_pull_data_api_paths(app, client, monkeypatch):
    # Busy => 409
    app.config["PULL_RUNNING_CHECK"] = lambda: True
    resp = client.post("/pull-data")
    assert resp.status_code == 409

    # Handler path => 200
    app.config["PULL_RUNNING_CHECK"] = lambda: False
    app.config["PULL_HANDLER"] = lambda: {"inserted": 1}
    resp = client.post("/pull-data")
    assert resp.status_code == 200

    # LLM not ready => 503
    app.config.pop("PULL_HANDLER", None)
    app.config["LLM_READY_CHECK"] = lambda: False
    resp = client.post("/pull-data")
    assert resp.status_code == 503

    # Start failure => 500
    app.config["LLM_READY_CHECK"] = lambda: True
    app.config["PULL_STARTER"] = lambda: False
    resp = client.post("/pull-data")
    assert resp.status_code == 500

    # Start success => 202
    app.config["PULL_STARTER"] = lambda: True
    resp = client.post("/pull-data")
    assert resp.status_code == 202


def test_update_and_ui_routes(app, client):
    # update-analysis should return ok when not busy.
    app.config["PULL_RUNNING_CHECK"] = lambda: False
    app.config["UPDATE_HANDLER"] = lambda: True
    resp = client.post("/update-analysis")
    assert resp.status_code == 200

    # UI pull-data redirect when busy.
    app.config["PULL_RUNNING_CHECK"] = lambda: True
    resp = client.post("/projects/module-3/pull-data")
    assert resp.status_code == 302

    # UI pull-data redirect when LLM not ready.
    app.config["PULL_RUNNING_CHECK"] = lambda: False
    app.config["LLM_READY_CHECK"] = lambda: False
    resp = client.post("/projects/module-3/pull-data")
    assert resp.status_code == 302

    # UI pull-data redirect when started successfully.
    app.config["LLM_READY_CHECK"] = lambda: True
    app.config["PULL_STARTER"] = lambda: True
    resp = client.post("/projects/module-3/pull-data")
    assert resp.status_code == 302

    # UI pull-data redirect when start fails (LLM ready).
    app.config["PULL_STARTER"] = lambda: False
    resp = client.post("/projects/module-3/pull-data")
    assert resp.status_code == 302

    # update-analysis UI route when busy.
    app.config["PULL_RUNNING_CHECK"] = lambda: True
    resp = client.post("/projects/module-3/update-analysis")
    assert resp.status_code == 302

    # update-analysis UI route when not busy.
    app.config["PULL_RUNNING_CHECK"] = lambda: False
    app.config["UPDATE_HANDLER"] = lambda: True
    resp = client.post("/projects/module-3/update-analysis")
    assert resp.status_code == 302


def test_cancel_pull_routes(app, client, monkeypatch):
    # When a pull is running, cancel should clear state and redirect.
    app.config["PULL_RUNNING_CHECK"] = lambda: True
    monkeypatch.setattr(pages, "_clear_pull_state", lambda: None)
    resp = client.post("/projects/module-3/cancel-pull")
    assert resp.status_code == 302

    # When not running, cancel should still redirect safely.
    app.config["PULL_RUNNING_CHECK"] = lambda: False
    resp = client.post("/projects/module-3/cancel-pull")
    assert resp.status_code == 302


def test_pull_status_endpoint(temp_paths, app, client, monkeypatch):
    # Create done file to exercise done_status parsing.
    (temp_paths / "pull.done").write_text("done")

    app.config["PULL_RUNNING_CHECK"] = lambda: False
    app.config["LLM_READY_CHECK"] = lambda: True

    resp = client.get("/projects/module-3/pull-status")
    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload["running"] is False
    assert payload["llm_ready"] is True
    assert payload["done"] is True


def test_pull_status_done_read_error(temp_paths, app, client, monkeypatch):
    # If DONE_PATH exists but can't be read, status should fall back to "unknown".
    (temp_paths / "pull.done").write_text("done")
    monkeypatch.setattr(builtins, "open", lambda *a, **k: (_ for _ in ()).throw(OSError("fail")))
    resp = client.get("/projects/module-3/pull-status")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "unknown"


def test_module_3_project_status_messages(app, client, temp_paths, monkeypatch):
    # Provide stable analysis results so rendering doesn't hit the DB.
    fake_results = {
        "total_applicants": 1,
        "year_2026": {
            "fall_2026_count": 1,
            "percent_international": 0.0,
            "average_metrics": {"avg_gpa": None, "avg_gre": None, "avg_gre_v": None, "avg_gre_aw": None},
            "avg_gpa_american_fall_2026": None,
            "acceptance_rate_fall_2026": 0.0,
            "avg_gpa_acceptances_fall_2026": None,
            "jhu_masters_cs": 0,
            "top_phd_acceptances_2026_raw": 0,
            "top_phd_acceptances_2026_llm": 0,
            "additional_question_1": 0.0,
            "additional_question_2": None,
        },
        "all_time": {
            "total_entries": 1,
            "percent_international": 0.0,
            "average_metrics": {"avg_gpa": None, "avg_gre": None, "avg_gre_v": None, "avg_gre_aw": None},
            "avg_gpa_american_fall_2026": None,
            "acceptance_rate_fall_2026": 0.0,
            "avg_gpa_acceptances_fall_2026": None,
            "jhu_masters_cs": 0,
            "top_phd_acceptances_2026_raw": 0,
            "top_phd_acceptances_2026_llm": 0,
            "additional_question_1": 0.0,
            "additional_question_2": None,
        },
    }
    monkeypatch.setattr(pages, "_read_cached_results", lambda: fake_results)
    monkeypatch.setattr(pages, "_compute_results", lambda: fake_results)
    monkeypatch.setattr(pages, "_write_cached_results", lambda results: None)
    monkeypatch.setattr(pages, "generate_pdf_report", lambda *a, **k: None)
    monkeypatch.setattr(pages, "get_latest_db_id", lambda: 1)
    monkeypatch.setattr(pages, "_read_latest_survey_id", lambda: 2)
    monkeypatch.setattr(pages, "_read_last_pull_job", lambda: None)

    # DONE_PATH statuses should produce a banner message.
    done_statuses = [
        "target_reached",
        "partial_new_entries",
        "no_new_entries",
        "no_more_entries",
        "no_new_data",
        "fetch_failed",
        "timeout",
        "error",
        "something_else",
    ]
    for status in done_statuses:
        (temp_paths / "pull.done").write_text(json.dumps({"status": status, "inserted": 1}))
        resp = client.get("/analysis")
        assert resp.status_code == 200

    # Invalid JSON in DONE_PATH should not crash (json decode error branch).
    (temp_paths / "pull.done").write_text("{not json")
    resp = client.get("/analysis")
    assert resp.status_code == 200

    # OSError reading DONE_PATH should be swallowed.
    real_open = builtins.open
    (temp_paths / "pull.done").write_text("ok")
    monkeypatch.setattr(builtins, "open", lambda *a, **k: (_ for _ in ()).throw(OSError("fail")))
    resp = client.get("/analysis")
    assert resp.status_code == 200

    # OSError removing DONE_PATH should be swallowed.
    monkeypatch.setattr(builtins, "open", real_open)
    monkeypatch.setattr(pages.os, "remove", lambda *_: (_ for _ in ()).throw(OSError("fail")))
    resp = client.get("/analysis")
    assert resp.status_code == 200

    # Query-string statuses should also map to messages.
    status_values = [
        "pull_started",
        "pull_running",
        "llm_not_ready",
        "analysis_updated",
        "pull_done",
        "pull_cancelled",
        "pull_timeout",
    ]
    pages.PULL_LAST_EXIT = 0
    for status in status_values:
        resp = client.get(f"/analysis?status={status}")
        assert resp.status_code == 200

    # Force a non-zero last exit to cover the error branch.
    pages.PULL_LAST_EXIT = 1
    resp = client.get("/analysis?status=pull_done")
    assert resp.status_code == 200

    # Cover the branch where PULL_LAST_EXIT is None.
    pages.PULL_LAST_EXIT = None
    resp = client.get("/analysis?status=pull_done")
    assert resp.status_code == 200


def test_module_3_project_compute_and_meta(app, client, temp_paths, monkeypatch):
    # Start with empty cache to exercise compute-and-write path.
    monkeypatch.setattr(pages, "_read_cached_results", lambda: None)

    # Provide results with _meta so analysis_updated_at is computed.
    fake_results = {
        "total_applicants": 1,
        "year_2026": {
            "fall_2026_count": 1,
            "percent_international": 0.0,
            "average_metrics": {"avg_gpa": None, "avg_gre": None, "avg_gre_v": None, "avg_gre_aw": None},
            "avg_gpa_american_fall_2026": None,
            "acceptance_rate_fall_2026": 0.0,
            "avg_gpa_acceptances_fall_2026": None,
            "jhu_masters_cs": 0,
            "top_phd_acceptances_2026_raw": 0,
            "top_phd_acceptances_2026_llm": 0,
            "additional_question_1": 0.0,
            "additional_question_2": None,
        },
        "all_time": {
            "total_entries": 1,
            "percent_international": 0.0,
            "average_metrics": {"avg_gpa": None, "avg_gre": None, "avg_gre_v": None, "avg_gre_aw": None},
            "avg_gpa_american_fall_2026": None,
            "acceptance_rate_fall_2026": 0.0,
            "avg_gpa_acceptances_fall_2026": None,
            "jhu_masters_cs": 0,
            "top_phd_acceptances_2026_raw": 0,
            "top_phd_acceptances_2026_llm": 0,
            "additional_question_1": 0.0,
            "additional_question_2": None,
        },
        "_meta": {"updated_at": time.time()},
    }
    monkeypatch.setattr(pages, "_compute_results", lambda: fake_results)
    monkeypatch.setattr(pages, "_write_cached_results", lambda results: None)
    monkeypatch.setattr(pages, "get_latest_db_id", lambda: None)
    monkeypatch.setattr(pages, "_read_latest_survey_id", lambda: None)
    monkeypatch.setattr(pages, "_read_last_pull_job", lambda: None)

    # Force report generation to raise to cover the exception branch.
    monkeypatch.setattr(pages, "generate_pdf_report", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("fail")))

    resp = client.get("/analysis")
    assert resp.status_code == 200

    # Now test invalid meta updated_at.
    fake_results["_meta"]["updated_at"] = "bad"
    resp = client.get("/analysis")
    assert resp.status_code == 200


def test_cached_results_report_generation_error(app, client, temp_paths, monkeypatch):
    # Cached results should still attempt PDF generation and swallow errors.
    fake_results = {
        "total_applicants": 1,
        "year_2026": {
            "fall_2026_count": 1,
            "percent_international": 0.0,
            "average_metrics": {"avg_gpa": None, "avg_gre": None, "avg_gre_v": None, "avg_gre_aw": None},
            "avg_gpa_american_fall_2026": None,
            "acceptance_rate_fall_2026": 0.0,
            "avg_gpa_acceptances_fall_2026": None,
            "jhu_masters_cs": 0,
            "top_phd_acceptances_2026_raw": 0,
            "top_phd_acceptances_2026_llm": 0,
            "additional_question_1": 0.0,
            "additional_question_2": None,
        },
        "all_time": {
            "total_entries": 1,
            "percent_international": 0.0,
            "average_metrics": {"avg_gpa": None, "avg_gre": None, "avg_gre_v": None, "avg_gre_aw": None},
            "avg_gpa_american_fall_2026": None,
            "acceptance_rate_fall_2026": 0.0,
            "avg_gpa_acceptances_fall_2026": None,
            "jhu_masters_cs": 0,
            "top_phd_acceptances_2026_raw": 0,
            "top_phd_acceptances_2026_llm": 0,
            "additional_question_1": 0.0,
            "additional_question_2": None,
        },
    }

    monkeypatch.setattr(pages, "_read_cached_results", lambda: fake_results)
    monkeypatch.setattr(pages, "generate_pdf_report", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("fail")))
    monkeypatch.setattr(pages, "get_latest_db_id", lambda: 1)
    monkeypatch.setattr(pages, "_read_latest_survey_id", lambda: None)
    monkeypatch.setattr(pages, "_read_last_pull_job", lambda: None)

    resp = client.get("/analysis")
    assert resp.status_code == 200


def test_module_3_project_remove_done_oserror(app, client, temp_paths, monkeypatch):
    # Ensure the DONE_PATH removal failure branch is exercised.
    (temp_paths / "pull.done").write_text(json.dumps({"status": "target_reached", "inserted": 1}))

    fake_results = {
        "total_applicants": 1,
        "year_2026": {
            "fall_2026_count": 1,
            "percent_international": 0.0,
            "average_metrics": {"avg_gpa": None, "avg_gre": None, "avg_gre_v": None, "avg_gre_aw": None},
            "avg_gpa_american_fall_2026": None,
            "acceptance_rate_fall_2026": 0.0,
            "avg_gpa_acceptances_fall_2026": None,
            "jhu_masters_cs": 0,
            "top_phd_acceptances_2026_raw": 0,
            "top_phd_acceptances_2026_llm": 0,
            "additional_question_1": 0.0,
            "additional_question_2": None,
        },
        "all_time": {
            "total_entries": 1,
            "percent_international": 0.0,
            "average_metrics": {"avg_gpa": None, "avg_gre": None, "avg_gre_v": None, "avg_gre_aw": None},
            "avg_gpa_american_fall_2026": None,
            "acceptance_rate_fall_2026": 0.0,
            "avg_gpa_acceptances_fall_2026": None,
            "jhu_masters_cs": 0,
            "top_phd_acceptances_2026_raw": 0,
            "top_phd_acceptances_2026_llm": 0,
            "additional_question_1": 0.0,
            "additional_question_2": None,
        },
    }
    monkeypatch.setattr(pages, "_read_cached_results", lambda: fake_results)
    monkeypatch.setattr(pages, "get_latest_db_id", lambda: 1)
    monkeypatch.setattr(pages, "_read_latest_survey_id", lambda: None)
    monkeypatch.setattr(pages, "_read_last_pull_job", lambda: None)
    monkeypatch.setattr(pages.os, "remove", lambda *_: (_ for _ in ()).throw(OSError("fail")))

    resp = client.get("/analysis")
    assert resp.status_code == 200


def test_run_update_analysis_paths(app):
    # If UPDATE_HANDLER is set, it should be invoked and returned.
    called = {"count": 0}

    def handler():
        called["count"] += 1
        return {"ok": True}

    app.config["UPDATE_HANDLER"] = handler
    with app.app_context():
        result = pages._run_update_analysis()
    assert called["count"] == 1
    assert result == {"ok": True}


def test_run_update_analysis_default_path(app, monkeypatch):
    # Without UPDATE_HANDLER, the default path should compute + write + report.
    app.config.pop("UPDATE_HANDLER", None)
    monkeypatch.setattr(pages, "_compute_results", lambda: {"year_2026": {}, "all_time": {}, "total_applicants": 0})
    monkeypatch.setattr(pages, "_write_cached_results", lambda *_: None)
    monkeypatch.setattr(pages, "generate_pdf_report", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("fail")))

    with app.app_context():
        result = pages._run_update_analysis()

    assert "year_2026" in result
