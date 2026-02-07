import os
import sys
import subprocess
import time
from flask import render_template, redirect, url_for, request
from . import bp
from M3_material.query_data import (
    count_fall_2026_entries,
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
LOCK_STALE_SECONDS = 900

PULL_PROCESS = None
PULL_LAST_EXIT = None
LAST_RESULTS = None


def _compute_results():
    return {
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


def _is_pull_running():
    global PULL_PROCESS, PULL_LAST_EXIT
    if PULL_PROCESS is None:
        if os.path.exists(LOCK_PATH):
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
    global LAST_RESULTS
    pull_running = _is_pull_running()
    status = request.args.get("status")
    message = None
    if not pull_running and os.path.exists(DONE_PATH):
        try:
            with open(DONE_PATH, "r") as f:
                done_status = f.read().strip()
        except OSError:
            done_status = ""
        try:
            os.remove(DONE_PATH)
        except OSError:
            pass

        if done_status == "success":
            message = "Pull is completed. You can now update analysis."
        elif done_status == "max_reached":
            message = "Pull is completed (max new records reached). You can now update analysis."
        elif done_status == "no_new_data":
            message = "Pull is completed. No new records were found, but you can now update analysis."
        elif done_status == "error":
            message = "Pull completed with errors. Check pull_data.log for details."
        else:
            message = "Pull is completed. You can now update analysis."
    if message is None:
        if status == "pull_started":
            message = "Pull Data started. This may take a minute. You can refresh to see new results."
        elif status == "pull_running":
            message = "Pull Data is already running. Update Analysis is disabled until it finishes."
        elif status == "analysis_updated":
            message = "Analysis refreshed with the latest available data."
        elif status == "pull_done" and PULL_LAST_EXIT == 0:
            message = "Pull Data finished successfully. Results updated."
        elif status == "pull_done" and PULL_LAST_EXIT not in (None, 0):
            message = "Pull Data finished with errors. Check pull_data.log for details."
        elif status == "pull_done":
            message = "Pull Data finished. You can click Update Analysis to refresh the page."

    if LAST_RESULTS is None:
        LAST_RESULTS = _compute_results()

    results = LAST_RESULTS
    return render_template(
        "project_module_3.html",
        results=results,
        pull_running=pull_running,
        status_message=message
    )


@bp.route("/projects/module-3/pull-data", methods=["POST"])
def pull_data():
    if _is_pull_running():
        return redirect(url_for("m3_pages.module_3_project", status="pull_running"))

    started = _start_pull()
    if not started:
        return redirect(url_for("m3_pages.module_3_project", status="pull_running"))
    return redirect(url_for("m3_pages.module_3_project", status="pull_started"))


@bp.route("/projects/module-3/update-analysis", methods=["POST"])
def update_analysis():
    global LAST_RESULTS
    if _is_pull_running():
        return redirect(url_for("m3_pages.module_3_project", status="pull_running"))
    LAST_RESULTS = _compute_results()
    return redirect(url_for("m3_pages.module_3_project", status="analysis_updated"))
