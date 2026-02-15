"""
Flask routes for Module 3 pages.

Responsibilities:
- Render the analysis dashboard and PDF link.
- Start/track/cancel the pull-data subprocess.
- Expose a small JSON status endpoint for the UI timer and LLM readiness.
"""

import os
import sys
import subprocess
import time
import json
import urllib.request
import urllib.error
import psycopg
from urllib.parse import urlsplit, urlunsplit
from flask import render_template, redirect, url_for, request, jsonify, current_app
from M3_material.reporting import generate_pdf_report
from . import bp
from M3_material.query_data import (
    build_analysis_results,
    get_latest_db_id
)

from db.db_config import get_db_config
from config import TARGET_NEW_RECORDS, LLM_HOST, LLM_PORT

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PULL_SCRIPT = os.path.join(BASE_DIR, "M2_material", "pull_data.py")
LOG_PATH = os.path.join(BASE_DIR, "db", "pull_data.log")
LOCK_PATH = os.path.join(BASE_DIR, "db", "pull_data.lock")
DONE_PATH = os.path.join(BASE_DIR, "db", "pull_data.done")
PROGRESS_PATH = os.path.join(BASE_DIR, "db", "pull_progress.json")
LATEST_SURVEY_PATH = os.path.join(BASE_DIR, "db", "latest_survey_id.txt")
LOCK_STALE_SECONDS = 900
MAX_NEW_RECORDS = TARGET_NEW_RECORDS
REPORT_PATH = os.path.join(BASE_DIR, "static", "reports", "module_3_report.pdf")
ANALYSIS_CACHE_PATH = os.path.join(BASE_DIR, "db", "analysis_cache.json")

PULL_PROCESS = None
PULL_LAST_EXIT = None


def _pid_running(pid):
    """Return True if the OS reports the PID is still alive."""
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _llm_status_url():
    """Compute the LLM status URL from environment settings."""
    host_url = os.getenv("LLM_HOST_URL")
    if host_url:
        parts = urlsplit(host_url)
        return urlunsplit((parts.scheme, parts.netloc, "/status", "", ""))
    return f"http://{LLM_HOST}:{LLM_PORT}/status"


def _is_llm_ready():
    """Check if the local LLM service reports ready."""
    url = _llm_status_url()
    try:
        with urllib.request.urlopen(url, timeout=1) as resp:
            if not (200 <= resp.status < 300):
                return False
            try:
                payload = json.loads(resp.read().decode("utf-8"))
            except json.JSONDecodeError:
                return False
            return bool(payload.get("model_loaded"))
    except (urllib.error.URLError, TimeoutError):
        return False


def _cfg(name, default):
    """Return app config override if set."""
    try:
        app = current_app._get_current_object()
    except RuntimeError:
        return default
    return app.config.get(name, default)


def _llm_ready():
    checker = _cfg("LLM_READY_CHECK", _is_llm_ready)
    return checker()


def _pull_running():
    checker = _cfg("PULL_RUNNING_CHECK", _is_pull_running)
    return checker()


def _start_pull_injected():
    starter = _cfg("PULL_STARTER", _start_pull)
    return starter()


def _analysis_cache_path():
    return _cfg("ANALYSIS_CACHE_PATH", ANALYSIS_CACHE_PATH)


def _report_path():
    return _cfg("REPORT_PATH", REPORT_PATH)


def _read_progress():
    """Read pull progress for UI status/ETA."""
    if not os.path.exists(PROGRESS_PATH):
        return None
    try:
        with open(PROGRESS_PATH, "r") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def _compute_results():
    """Compute all stats for both 2026 cohort and all-time."""
    compute = _cfg("COMPUTE_RESULTS", build_analysis_results)
    return compute()


def _read_cached_results():
    """Load cached analysis JSON if present and valid."""
    cache_path = _analysis_cache_path()
    if not os.path.exists(cache_path):
        return None
    try:
        with open(cache_path, "r") as f:
            data = json.load(f)
            if not isinstance(data, dict):
                return None
            if "year_2026" in data and "all_time" in data:
                return data
            return None
    except (OSError, json.JSONDecodeError):
        return None


def _write_cached_results(results):
    """Persist analysis results to disk for fast page loads."""
    cache_path = _analysis_cache_path()
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    with open(cache_path, "w") as f:
        payload = dict(results)
        payload["_meta"] = {"updated_at": time.time()}
        json.dump(payload, f, indent=2)


def _read_latest_survey_id():
    """Read latest survey id from disk if available."""
    if not os.path.exists(LATEST_SURVEY_PATH):
        return None
    try:
        with open(LATEST_SURVEY_PATH, "r") as f:
            value = f.read().strip()
            return int(value) if value else None
    except (OSError, ValueError):
        return None


def _read_last_pull_job():
    """Return the most recent pull job status from the DB."""
    try:
        with psycopg.connect(**get_db_config()) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT status, inserted, processed, updated_at, error
                    FROM pull_jobs
                    ORDER BY updated_at DESC
                    LIMIT 1
                    """
                )
                row = cur.fetchone()
                if not row:
                    return None
                return {
                    "status": row[0],
                    "inserted": row[1],
                    "processed": row[2],
                    "updated_at": row[3],
                    "error": row[4],
                }
    except Exception:
        return None


def _is_pull_running():
    """Determine whether a pull is currently running."""
    global PULL_PROCESS, PULL_LAST_EXIT
    if PULL_PROCESS is None:
        if os.path.exists(DONE_PATH):
            if os.path.exists(LOCK_PATH):
                try:
                    os.remove(LOCK_PATH)
                except OSError:
                    pass
            return False
        if os.path.exists(LOCK_PATH):
            try:
                with open(LOCK_PATH, "r") as f:
                    pid_text = f.read().strip()
                if not pid_text:
                    os.remove(LOCK_PATH)
                    return False
                if pid_text == "starting":
                    age = time.time() - os.path.getmtime(LOCK_PATH)
                    if age > 10:
                        os.remove(LOCK_PATH)
                        return False
                    return True
                if pid_text.isdigit() and not _pid_running(int(pid_text)):
                    os.remove(LOCK_PATH)
                    return False
            except OSError:
                pass
            try:
                age = time.time() - os.path.getmtime(LOCK_PATH)
            except OSError:
                return True
            if age > LOCK_STALE_SECONDS:
                try:
                    os.remove(LOCK_PATH)
                except OSError:
                    pass
                return False
            return True
        return False
    if PULL_PROCESS.poll() is None:
        return True
    PULL_LAST_EXIT = PULL_PROCESS.returncode
    PULL_PROCESS = None
    return False


def _clear_pull_state():
    """Terminate any running pull and clear lock/progress files."""
    global PULL_PROCESS, PULL_LAST_EXIT
    if PULL_PROCESS is not None and PULL_PROCESS.poll() is None:
        try:
            PULL_PROCESS.terminate()
            PULL_PROCESS.wait(timeout=3)
        except Exception:
            try:
                PULL_PROCESS.kill()
            except Exception:
                pass
    PULL_PROCESS = None
    PULL_LAST_EXIT = None
    for path in (LOCK_PATH, DONE_PATH, PROGRESS_PATH):
        try:
            if os.path.exists(path):
                os.remove(path)
        except OSError:
            pass


def _start_pull():
    """Start the pull subprocess and register it in the lock file."""
    global PULL_PROCESS, PULL_LAST_EXIT
    if _pull_running():
        return False
    if not _llm_ready():
        return False

    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    log_file = open(LOG_PATH, "a")
    try:
        os.makedirs(os.path.dirname(LOCK_PATH), exist_ok=True)
        with open(LOCK_PATH, "w") as f:
            f.write("starting")
    except OSError:
        pass
    try:
        PULL_PROCESS = subprocess.Popen(
            [sys.executable, PULL_SCRIPT, "--lock", LOCK_PATH],
            cwd=BASE_DIR,
            stdout=log_file,
            stderr=log_file
        )
        # Overwrite lock with PID once started so it isn't stuck at "starting"
        try:
            with open(LOCK_PATH, "w") as f:
                f.write(str(PULL_PROCESS.pid))
        except OSError:
            pass
        PULL_LAST_EXIT = None
        return True
    except Exception as e:
        try:
            log_file.write(f"Failed to start pull: {e}\n")
        except Exception:
            pass
        try:
            if os.path.exists(LOCK_PATH):
                os.remove(LOCK_PATH)
        except OSError:
            pass
        return False
    finally:
        log_file.close()


@bp.route("/projects/module-3")
def module_3_project():
    """Render the Module 3 dashboard with current analysis results."""
    pull_running = _pull_running()
    llm_ready = _llm_ready()
    status = request.args.get("status")
    message = None
    if not pull_running and os.path.exists(DONE_PATH):
        done_status = ""
        done_inserted = None
        done_duplicates = None
        try:
            with open(DONE_PATH, "r") as f:
                try:
                    data = json.load(f)
                    done_status = data.get("status", "")
                    done_inserted = data.get("inserted")
                    done_duplicates = data.get("duplicates")
                except json.JSONDecodeError:
                    done_status = f.read().strip()
        except OSError:
            done_status = ""
        try:
            os.remove(DONE_PATH)
        except OSError:
            pass

        if done_status == "target_reached":
            count_text = done_inserted if done_inserted is not None else "new"
            message = f"Pull is completed with {count_text} records. You can now update analysis."
        elif done_status == "partial_new_entries":
            count_text = done_inserted if done_inserted is not None else "some"
            message = (
                f"Pull is completed with {count_text} new records "
                f"(less than {MAX_NEW_RECORDS} available). You can now update analysis."
            )
        elif done_status == "no_new_entries":
            message = "Pull stopped: the most recent GradCafe submission is already in the database."
        elif done_status == "no_more_entries":
            message = "Pull stopped: no more applicant entries were found. You can now update analysis."
        elif done_status == "no_new_data":
            message = "Pull is completed. No new records were found, but you can now update analysis."
        elif done_status == "fetch_failed":
            message = "Pull stopped after repeated fetch failures. GradCafe may be blocking requests. You can try again later."
        elif done_status == "timeout":
            message = "Pull timed out before completing. You can try again or update analysis with current data."
        elif done_status == "error":
            message = "Pull completed with errors. Check pull_data.log for details."
        elif done_status:
            message = "Pull is completed. You can now update analysis."
    if message is None:
        if status == "pull_started":
            message = "Pull Data started. This may take a minute. You can refresh to see new results."
        elif status == "pull_running":
            message = "Pull Data is already running. Update Analysis is disabled until it finishes."
        elif status == "llm_not_ready":
            message = "LLM server is not ready yet. Start it (or wait a moment) before pulling new data."
        elif status == "analysis_updated":
            message = "Analysis refreshed with the latest available data."
        elif status == "pull_done" and PULL_LAST_EXIT == 0:
            message = "Pull Data finished successfully. Results updated."
        elif status == "pull_done" and PULL_LAST_EXIT not in (None, 0):
            message = "Pull Data finished with errors. Check pull_data.log for details."
        elif status == "pull_done":
            message = "Pull Data finished. You can click Update Analysis to refresh the page."
        elif status == "pull_cancelled":
            message = "Pull cancelled. You can start a new pull or update analysis."
        elif status == "pull_timeout":
            message = "Pull timed out. You can try again or update analysis with current data."

    results = _read_cached_results()
    if results is None:
        results = _compute_results()
        _write_cached_results(results)
        report_path = _report_path()
        if not os.path.exists(report_path):
            try:
                generate_pdf_report(results, report_path)
            except Exception:
                pass
    else:
        report_path = _report_path()
        if not os.path.exists(report_path):
            try:
                generate_pdf_report(results, report_path)
            except Exception:
                pass
    analysis_updated_at = None
    meta = results.get("_meta") if isinstance(results, dict) else None
    if meta and meta.get("updated_at"):
        try:
            analysis_updated_at = time.strftime(
                "%Y-%m-%d %H:%M:%S",
                time.localtime(float(meta.get("updated_at")))
            )
        except (TypeError, ValueError):
            analysis_updated_at = None
    latest_db_id = get_latest_db_id()
    latest_survey_id = _read_latest_survey_id()
    last_pull_job = _read_last_pull_job()
    return render_template(
        "project_module_3.html",
        results_2026=results.get("year_2026", {}),
        results_all=results.get("all_time", {}),
        total_applicants=results.get("total_applicants"),
        pull_running=pull_running,
        llm_ready=llm_ready,
        pull_progress=_read_progress(),
        status_message=message,
        max_new_records=MAX_NEW_RECORDS,
        latest_db_id=latest_db_id,
        latest_survey_id=latest_survey_id,
        last_pull_job=last_pull_job,
        analysis_updated_at=analysis_updated_at,
        report_url=url_for("static", filename="reports/module_3_report.pdf")
    )


@bp.route("/analysis")
def analysis_page():
    """Alias for the Module 3 analysis dashboard."""
    return module_3_project()


def _run_update_analysis():
    updater = _cfg("UPDATE_HANDLER", None)
    if updater:
        return updater()
    results = _compute_results()
    _write_cached_results(results)
    try:
        generate_pdf_report(results, _report_path())
    except Exception:
        pass
    return results


@bp.route("/pull-data", methods=["POST"])
def pull_data_api():
    """JSON endpoint for triggering a pull."""
    if _pull_running():
        return jsonify({"busy": True}), 409

    handler = _cfg("PULL_HANDLER", None)
    if handler:
        result = handler()
        return jsonify({"ok": True, "result": result}), 200

    if not _llm_ready():
        return jsonify({"ok": False, "error": "llm_not_ready"}), 503

    started = _start_pull_injected()
    if not started:
        return jsonify({"ok": False, "error": "start_failed"}), 500
    return jsonify({"ok": True}), 202


@bp.route("/update-analysis", methods=["POST"])
def update_analysis_api():
    """JSON endpoint to recompute analysis."""
    if _pull_running():
        return jsonify({"busy": True}), 409
    _run_update_analysis()
    return jsonify({"ok": True}), 200


@bp.route("/projects/module-3/pull-data", methods=["POST"])
def pull_data():
    """Trigger a background pull if LLM is ready and no pull is running."""
    if _pull_running():
        return redirect(url_for("m3_pages.module_3_project", status="pull_running"))
    if not _llm_ready():
        return redirect(url_for("m3_pages.module_3_project", status="llm_not_ready"))

    started = _start_pull_injected()
    if not started:
        return redirect(url_for("m3_pages.module_3_project", status="llm_not_ready"))
    return redirect(url_for("m3_pages.module_3_project", status="pull_started"))


@bp.route("/projects/module-3/cancel-pull", methods=["POST"])
def cancel_pull():
    if _pull_running():
        _clear_pull_state()
        return redirect(url_for("m3_pages.module_3_project", status="pull_cancelled"))
    return redirect(url_for("m3_pages.module_3_project"))


@bp.route("/projects/module-3/update-analysis", methods=["POST"])
def update_analysis():
    """Recompute analysis and regenerate the PDF report."""
    if _pull_running():
        return redirect(url_for("m3_pages.module_3_project", status="pull_running"))
    _run_update_analysis()
    return redirect(url_for("m3_pages.module_3_project", status="analysis_updated"))


@bp.route("/projects/module-3/pull-status")
def pull_status():
    """Return JSON status for UI polling (LLM ready + progress)."""
    running = _pull_running()
    done_status = None
    if os.path.exists(DONE_PATH):
        try:
            with open(DONE_PATH, "r") as f:
                done_status = f.read().strip() or "unknown"
        except OSError:
            done_status = "unknown"
    return jsonify({
        "running": running,
        "llm_ready": _llm_ready(),
        "progress": _read_progress(),
        "done": bool(done_status),
        "status": done_status
    })
