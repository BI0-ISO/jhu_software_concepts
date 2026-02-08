import os
import sys
import subprocess
import time
import json
import urllib.request
import urllib.error
from urllib.parse import urlsplit, urlunsplit
from flask import render_template, redirect, url_for, request, jsonify
from M3_material.reporting import generate_pdf_report
from . import bp
from M3_material.query_data import (
    count_fall_2026_entries,
    count_total_applicants,
    percent_international_students,
    average_metrics_all_applicants,
    avg_gpa_american_fall_2026,
    acceptance_rate_fall_2026,
    avg_gpa_acceptances_fall_2026,
    count_jhu_masters_cs,
    count_top_phd_acceptances_2026_raw_university,
    count_top_phd_acceptances_2026_llm,
    additional_question_1,
    additional_question_2
)

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PULL_SCRIPT = os.path.join(BASE_DIR, "M2_material", "pull_data.py")
LOG_PATH = os.path.join(BASE_DIR, "db", "pull_data.log")
LOCK_PATH = os.path.join(BASE_DIR, "db", "pull_data.lock")
DONE_PATH = os.path.join(BASE_DIR, "db", "pull_data.done")
PROGRESS_PATH = os.path.join(BASE_DIR, "db", "pull_progress.json")
LOCK_STALE_SECONDS = 900
MAX_NEW_RECORDS = 25  # target new records per pull
REPORT_PATH = os.path.join(BASE_DIR, "static", "reports", "module_3_report.pdf")
ANALYSIS_CACHE_PATH = os.path.join(BASE_DIR, "db", "analysis_cache.json")

PULL_PROCESS = None
PULL_LAST_EXIT = None


def _pid_running(pid):
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _llm_status_url():
    host_url = os.getenv("LLM_HOST_URL")
    if host_url:
        parts = urlsplit(host_url)
        return urlunsplit((parts.scheme, parts.netloc, "/status", "", ""))
    host = os.getenv("LLM_HOST", "127.0.0.1")
    port = os.getenv("LLM_PORT", "8000")
    return f"http://{host}:{port}/status"


def _is_llm_ready():
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


def _read_progress():
    if not os.path.exists(PROGRESS_PATH):
        return None
    try:
        with open(PROGRESS_PATH, "r") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def _compute_results():
    return {
        "total_applicants": count_total_applicants(),
        "fall_2026_count": count_fall_2026_entries(),
        "percent_international": percent_international_students(),
        "average_metrics": average_metrics_all_applicants(),
        "avg_gpa_american_fall_2026": avg_gpa_american_fall_2026(),
        "acceptance_rate_fall_2026": acceptance_rate_fall_2026(),
        "avg_gpa_acceptances_fall_2026": avg_gpa_acceptances_fall_2026(),
        "jhu_masters_cs": count_jhu_masters_cs(),
        "top_phd_acceptances_2026_raw": count_top_phd_acceptances_2026_raw_university(),
        "top_phd_acceptances_2026_llm": count_top_phd_acceptances_2026_llm(),
        "additional_question_1": additional_question_1(),
        "additional_question_2": additional_question_2(),
    }


def _read_cached_results():
    if not os.path.exists(ANALYSIS_CACHE_PATH):
        return None
    try:
        with open(ANALYSIS_CACHE_PATH, "r") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def _write_cached_results(results):
    os.makedirs(os.path.dirname(ANALYSIS_CACHE_PATH), exist_ok=True)
    with open(ANALYSIS_CACHE_PATH, "w") as f:
        json.dump(results, f, indent=2)


def _is_pull_running():
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


def _start_pull():
    global PULL_PROCESS, PULL_LAST_EXIT
    if _is_pull_running():
        return False
    if not _is_llm_ready():
        return False

    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    log_file = open(LOG_PATH, "a")
    try:
        with open(LOCK_PATH, "w") as f:
            f.write("starting")
    except OSError:
        pass
    PULL_PROCESS = subprocess.Popen(
        [sys.executable, PULL_SCRIPT, "--lock", LOCK_PATH],
        cwd=BASE_DIR,
        stdout=log_file,
        stderr=log_file
    )
    log_file.close()
    PULL_LAST_EXIT = None
    return True


@bp.route("/projects/module-3")
def module_3_project():
    pull_running = _is_pull_running()
    llm_ready = _is_llm_ready()
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
            message = f"Pull is completed with {count_text} new records (less than 200 available). You can now update analysis."
        elif done_status == "no_new_entries":
            message = "Pull stopped: the most recent GradCafe submission is already in the database."
        elif done_status == "no_more_entries":
            message = "Pull stopped: no more applicant entries were found. You can now update analysis."
        elif done_status == "no_new_data":
            message = "Pull is completed. No new records were found, but you can now update analysis."
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

    results = _read_cached_results()
    if results is None:
        results = _compute_results()
        _write_cached_results(results)
        if not os.path.exists(REPORT_PATH):
            try:
                generate_pdf_report(results, REPORT_PATH)
            except Exception:
                pass
    elif not os.path.exists(REPORT_PATH):
        try:
            generate_pdf_report(results, REPORT_PATH)
        except Exception:
            pass
    return render_template(
        "project_module_3.html",
        results=results,
        pull_running=pull_running,
        llm_ready=llm_ready,
        pull_progress=_read_progress(),
        status_message=message,
        max_new_records=MAX_NEW_RECORDS,
        report_url=url_for("static", filename="reports/module_3_report.pdf")
    )


@bp.route("/projects/module-3/pull-data", methods=["POST"])
def pull_data():
    if _is_pull_running():
        return redirect(url_for("m3_pages.module_3_project", status="pull_running"))
    if not _is_llm_ready():
        return redirect(url_for("m3_pages.module_3_project", status="llm_not_ready"))

    started = _start_pull()
    if not started:
        return redirect(url_for("m3_pages.module_3_project", status="llm_not_ready"))
    return redirect(url_for("m3_pages.module_3_project", status="pull_started"))


@bp.route("/projects/module-3/update-analysis", methods=["POST"])
def update_analysis():
    if _is_pull_running():
        return redirect(url_for("m3_pages.module_3_project", status="pull_running"))
    results = _compute_results()
    _write_cached_results(results)
    try:
        generate_pdf_report(results, REPORT_PATH)
    except Exception:
        pass
    return redirect(url_for("m3_pages.module_3_project", status="analysis_updated"))


@bp.route("/projects/module-3/pull-status")
def pull_status():
    running = _is_pull_running()
    done_status = None
    if os.path.exists(DONE_PATH):
        try:
            with open(DONE_PATH, "r") as f:
                done_status = f.read().strip() or "unknown"
        except OSError:
            done_status = "unknown"
    return jsonify({
        "running": running,
        "llm_ready": _is_llm_ready(),
        "progress": _read_progress(),
        "done": bool(done_status),
        "status": done_status
    })
