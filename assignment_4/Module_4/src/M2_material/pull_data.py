"""
Pull pipeline for Module 3.

Flow:
1) Determine the latest ID already stored in the database.
2) Scrape GradCafe starting after that ID, up to the latest survey ID.
3) Clean raw HTML into structured records.
4) Standardize program/university with the local LLM.
5) Normalize fields and insert into Postgres.
6) Write progress to JSON for the UI and finalize status.
"""

import os
import sys
import json
import time
import argparse
from typing import Optional
import urllib.request
import urllib.error

import psycopg

from scrape import scrape_data, get_last_stop_reason, get_last_attempted_id, get_latest_survey_id
from clean import clean_data

# -------- Paths and config --------
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(BASE_DIR)

from config import (
    BASE_DIR as ROOT_DIR,
    DB_DIR,
    TARGET_NEW_RECORDS,
    LLM_HOST_URL,
    LLM_TIMEOUT,
    LLM_BATCH_SIZE,
    PULL_MAX_SECONDS,
)

DATA_PATH = os.path.join(ROOT_DIR, "M3_material", "data", "extra_llm_applicant_data.json")
STATE_PATH = os.path.join(DB_DIR, "last_scraped_id.txt")
LAST_ENTRIES_PATH = os.path.join(DB_DIR, "last_100_entries.json")
DONE_PATH = os.path.join(DB_DIR, "pull_data.done")
LATEST_SURVEY_PATH = os.path.join(DB_DIR, "latest_survey_id.txt")
PROGRESS_PATH = os.path.join(DB_DIR, "pull_progress.json")

from db.db_config import DB_CONFIG
from db.migrate import migrate
from db.normalize import normalize_record

USE_LLM = os.getenv("USE_LLM", "1") == "1"
_LLM_AVAILABLE = None
_LLM_WARNED = False


def _extract_entry_id(url: Optional[str]) -> Optional[int]:
    """Parse the numeric result ID from a GradCafe URL."""
    if not url:
        return None
    try:
        return int(url.rstrip("/").split("/")[-1])
    except (ValueError, IndexError):
        return None


def _read_last_scraped_id() -> Optional[int]:
    """Read the last attempted ID from disk (legacy fallback)."""
    if os.path.exists(STATE_PATH):
        try:
            with open(STATE_PATH, "r") as f:
                value = f.read().strip()
                return int(value) if value else None
        except (OSError, ValueError):
            return None
    return None


def _write_last_scraped_id(value: int) -> None:
    """Persist the last attempted ID to disk."""
    os.makedirs(DB_DIR, exist_ok=True)
    with open(STATE_PATH, "w") as f:
        f.write(str(value))


def _infer_last_id_from_file() -> Optional[int]:
    """Fallback: infer max ID from the local JSONL file."""
    if not os.path.exists(DATA_PATH):
        return None

    max_id = None
    try:
        with open(DATA_PATH, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                entry_id = _extract_entry_id(record.get("url"))
                if entry_id is not None and (max_id is None or entry_id > max_id):
                    max_id = entry_id
    except OSError:
        return None

    return max_id


def _get_max_entry_id_from_db(conn) -> Optional[int]:
    """Primary source of truth: max result ID already in the database."""
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT MAX(SUBSTRING(url FROM '/(\\d+)$')::int)
                FROM applicants
                WHERE url ~ '/\\d+$'
            """)
            value = cur.fetchone()[0]
            return int(value) if value is not None else None
    except Exception:
        return None



def ensure_table(conn):
    """Ensure the applicants table exists with the expected schema."""
    migrate()


def insert_new_records(conn, records):
    """Insert new records into the DB, skipping duplicates by URL."""
    inserted = 0
    duplicates = 0
    with conn.cursor() as cur:
        for r in records:
            url = r.get("url")
            if url:
                cur.execute("SELECT 1 FROM applicants WHERE url = %s", (url,))
                if cur.fetchone():
                    duplicates += 1
                    continue
            cur.execute("""
                INSERT INTO applicants (
                    program, comments, date_added, acceptance_date, url, status, term, us_or_international, gpa, gre, gre_v, gre_aw,
                    degree, llm_generated_program, llm_generated_university
                ) VALUES (
                    %(program)s, %(comments)s, %(date_added)s, %(acceptance_date)s, %(url)s, %(status)s, %(term)s, %(us_or_international)s, %(gpa)s, %(gre)s, %(gre_v)s, %(gre_aw)s,
                    %(degree)s, %(llm_generated_program)s, %(llm_generated_university)s
                )
            """, r)
            inserted += 1
    return inserted, duplicates


def url_exists(conn, url):
    """Return True if the given URL already exists in the DB."""
    if not url:
        return False
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM applicants WHERE url = %s", (url,))
        return cur.fetchone() is not None


def write_last_entries(conn, path, limit=100):
    """Write the newest N entries to disk for debugging."""
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM applicants ORDER BY p_id DESC LIMIT %s", (limit,))
        rows = cur.fetchall()
        columns = [desc[0] for desc in cur.description]
    entries = [dict(zip(columns, row)) for row in rows]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(entries, f, indent=2, default=str)


def _write_progress(status, inserted, duplicates, processed, target, started_at, last_attempted=None):
    """Write progress for UI polling and ETA estimates."""
    try:
        os.makedirs(DB_DIR, exist_ok=True)
        payload = {
            "status": status,
            "inserted": inserted,
            "duplicates": duplicates,
            "processed": processed,
            "target": target,
            "started_at": started_at,
            "updated_at": time.time(),
            "elapsed_seconds": int(time.time() - started_at),
            "last_attempted": last_attempted,
        }
        with open(PROGRESS_PATH, "w") as f:
            json.dump(payload, f)
    except OSError:
        pass


def _log_event(event: str, **fields) -> None:
    """Emit a structured JSON log line (captured in pull_data.log)."""
    payload = {"event": event, "ts": time.time(), **fields}
    try:
        print(json.dumps(payload))
    except Exception:
        print(f"[event:{event}] {fields}")


def _init_pull_job(conn, target):
    """Insert a pull job row and return its id."""
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO pull_jobs (status, target) VALUES (%s, %s) RETURNING id",
            ("running", target),
        )
        return cur.fetchone()[0]


def _update_pull_job(conn, job_id, status, inserted, duplicates, processed, last_attempted=None, error=None):
    """Update pull job status/metrics in the database."""
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE pull_jobs
               SET status = %s,
                   updated_at = NOW(),
                   inserted = %s,
                   duplicates = %s,
                   processed = %s,
                   last_attempted = %s,
                   error = %s
             WHERE id = %s
            """,
            (status, inserted, duplicates, processed, last_attempted, error, job_id),
        )


def _standardize_with_llm_batch(rows: list[dict]) -> list[dict]:
    """Call the local LLM service to standardize program/university names."""
    global _LLM_AVAILABLE, _LLM_WARNED
    if not USE_LLM:
        raise RuntimeError("LLM standardization is required. Set USE_LLM=1 and start the LLM server.")
    if _LLM_AVAILABLE is None:
        payload = {"rows": [{"program": "", "university": ""}]}
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            LLM_HOST_URL,
            data=data,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=min(5.0, LLM_TIMEOUT)) as resp:
                resp.read()
            _LLM_AVAILABLE = True
        except Exception as e:
            _LLM_AVAILABLE = False
            if not _LLM_WARNED:
                _LLM_WARNED = True
                print(f"LLM standardization unavailable: {e}")
    if not _LLM_AVAILABLE:
        raise RuntimeError("LLM standardization unavailable. Start the LLM server before pulling data.")

    payload = {
        "rows": [
            {
                "program": row.get("program") or "",
                "university": row.get("university") or "",
            }
            for row in rows
        ]
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        LLM_HOST_URL,
        data=data,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=LLM_TIMEOUT) as resp:
            resp_json = json.loads(resp.read().decode("utf-8"))
        llm_rows = resp_json.get("rows") or []
        if len(llm_rows) != len(rows):
            raise RuntimeError("LLM returned an unexpected number of rows.")
        for base_row, llm_row in zip(rows, llm_rows):
            base_row["llm_generated_program"] = llm_row.get("llm_generated_program") or base_row.get("program") or ""
            base_row["llm_generated_university"] = llm_row.get("llm_generated_university") or base_row.get("university") or ""
        return rows
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, TimeoutError, RuntimeError) as e:
        if len(rows) > 1:
            mid = len(rows) // 2
            left = _standardize_with_llm_batch(rows[:mid])
            right = _standardize_with_llm_batch(rows[mid:])
            return left + right
        raise RuntimeError(f"LLM standardization failed: {e}")


def main():
    """End-to-end pull for one batch of new records."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--lock", dest="lock_path", default=None)
    args = parser.parse_args()

    lock_path = args.lock_path
    status = "unknown"
    inserted_total = 0
    duplicates_total = 0
    processed_total = 0
    last_attempted = None
    latest_id = None
    started_at = time.time()
    target_new = TARGET_NEW_RECORDS
    job_id = None
    if lock_path:
        try:
            with open(lock_path, "w") as f:
                f.write(str(os.getpid()))
        except OSError:
            lock_path = None

    conn = None
    try:
        conn = psycopg.connect(**DB_CONFIG, autocommit=True)
        ensure_table(conn)

        last_id = _get_max_entry_id_from_db(conn)
        if last_id is None:
            last_id = _read_last_scraped_id()
        if last_id is None:
            last_id = _infer_last_id_from_file()
        if last_id is None:
            last_id = 950000

        latest_id = get_latest_survey_id()
        if latest_id is not None:
            os.makedirs(DB_DIR, exist_ok=True)
            with open(LATEST_SURVEY_PATH, "w") as f:
                f.write(str(latest_id))

        if latest_id is not None and last_id >= latest_id:
            print(f"No new entries: latest survey id is {latest_id}, already scraped up to {last_id}.")
            status = "no_new_entries"
            write_last_entries(conn, LAST_ENTRIES_PATH)
            return

        start_entry = last_id + 1
        end_entry = latest_id + 1 if latest_id is not None else None
        remaining_ids = latest_id - last_id if latest_id is not None else None
        target_new = min(TARGET_NEW_RECORDS, remaining_ids) if remaining_ids is not None else TARGET_NEW_RECORDS

        reached_target = False

        job_id = _init_pull_job(conn, target_new)
        _log_event("pull_started", target=target_new, start_id=last_id + 1, latest_id=latest_id)
        _write_progress("running", inserted_total, duplicates_total, processed_total, target_new, started_at)
        _update_pull_job(conn, job_id, "running", inserted_total, duplicates_total, processed_total, last_attempted)

        any_pages = False
        batch = []
        for page in scrape_data(
            start_entry,
            end_entry,
            stop_on_placeholder_streak=(latest_id is None),
            max_seconds=PULL_MAX_SECONDS,
        ):
            any_pages = True
            cleaned = clean_data([page])
            cleaned_row = cleaned[0]
            processed_total += 1
            last_attempted = get_last_attempted_id()
            _write_progress("running", inserted_total, duplicates_total, processed_total, target_new, started_at, last_attempted)
            if job_id:
                _update_pull_job(conn, job_id, "running", inserted_total, duplicates_total, processed_total, last_attempted)

            if url_exists(conn, cleaned_row.get("url")):
                duplicates_total += 1
                _write_progress("running", inserted_total, duplicates_total, processed_total, target_new, started_at)
                if job_id:
                    _update_pull_job(conn, job_id, "running", inserted_total, duplicates_total, processed_total, last_attempted)
                continue

            batch.append(cleaned_row)
            if len(batch) >= max(1, LLM_BATCH_SIZE):
                standardized_rows = _standardize_with_llm_batch(batch)
                normalized = [normalize_record(r) for r in standardized_rows]
                inserted, duplicates = insert_new_records(conn, normalized)
                inserted_total += inserted
                duplicates_total += duplicates
                batch = []
                _write_progress("running", inserted_total, duplicates_total, processed_total, target_new, started_at)

                if inserted_total >= target_new:
                    reached_target = True
                    break

        if batch and not reached_target:
            standardized_rows = _standardize_with_llm_batch(batch)
            normalized = [normalize_record(r) for r in standardized_rows]
            inserted, duplicates = insert_new_records(conn, normalized)
            inserted_total += inserted
            duplicates_total += duplicates
            batch = []
            _write_progress("running", inserted_total, duplicates_total, processed_total, target_new, started_at)
            if job_id:
                _update_pull_job(conn, job_id, "running", inserted_total, duplicates_total, processed_total, last_attempted)

        write_last_entries(conn, LAST_ENTRIES_PATH)

        if not any_pages:
            stop_reason = get_last_stop_reason()
            if stop_reason == "placeholder_streak":
                print("No more applicant entries found (placeholder streak).")
                status = "no_more_entries"
            elif stop_reason == "error_streak":
                print("Pull stopped after too many failed fetches.")
                status = "fetch_failed"
            elif stop_reason == "timeout":
                print("Pull timed out while fetching entries.")
                status = "timeout"
            else:
                print("No new pages found.")
                status = "no_new_data"
            last_attempted = get_last_attempted_id()
            if last_attempted is not None:
                _write_last_scraped_id(last_attempted)
            _write_progress(status, inserted_total, duplicates_total, processed_total, target_new, started_at)
            if job_id:
                _update_pull_job(conn, job_id, status, inserted_total, duplicates_total, processed_total, last_attempted)
            return

        last_attempted = get_last_attempted_id()
        if last_attempted is not None:
            _write_last_scraped_id(last_attempted)

        print(f"Inserted {inserted_total} new records, {duplicates_total} duplicates skipped. Last scraped id: {last_attempted}")
        _log_event("pull_finished", status=status, inserted=inserted_total, duplicates=duplicates_total, last_attempted=last_attempted)
        stop_reason = get_last_stop_reason()
        if stop_reason == "placeholder_streak":
            if inserted_total == 0:
                status = "no_more_entries"
            else:
                status = "partial_new_entries"
        elif stop_reason == "timeout":
            status = "timeout"
        elif stop_reason == "error_streak":
            status = "fetch_failed"
        elif latest_id is not None and last_attempted is not None and last_attempted >= latest_id:
            if inserted_total == 0:
                status = "no_new_entries"
            else:
                status = "partial_new_entries"
        elif inserted_total == 0:
            status = "no_new_data"
        else:
            status = "target_reached" if reached_target else "success"
    except Exception as e:
        status = "error"
        print(f"Pull failed: {e}")
        _log_event("pull_failed", error=str(e))
    finally:
        try:
            os.makedirs(DB_DIR, exist_ok=True)
            with open(DONE_PATH, "w") as f:
                json.dump({
                    "status": status,
                    "inserted": inserted_total,
                    "duplicates": duplicates_total,
                    "last_attempted": last_attempted
                }, f)
        except OSError:
            pass
        _write_progress(status, inserted_total, duplicates_total, processed_total, target_new, started_at)
        if conn is not None and job_id:
            try:
                _update_pull_job(conn, job_id, status, inserted_total, duplicates_total, processed_total, last_attempted, error=None if status != "error" else "error")
            except Exception:
                pass
        if lock_path and os.path.exists(lock_path):
            try:
                os.remove(lock_path)
            except OSError:
                pass
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass


if __name__ == "__main__":
    main()
