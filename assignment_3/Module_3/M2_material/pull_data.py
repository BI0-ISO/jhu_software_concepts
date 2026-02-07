import os
import sys
import json
import time
import argparse
from typing import Optional

import psycopg

from scrape import scrape_data
from clean import clean_data

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DB_DIR = os.path.join(BASE_DIR, "db")
DATA_PATH = os.path.join(BASE_DIR, "M3_material", "data", "llm_extend_applicant_data.json")
STATE_PATH = os.path.join(DB_DIR, "last_scraped_id.txt")
DONE_PATH = os.path.join(DB_DIR, "pull_data.done")

sys.path.append(BASE_DIR)
from db.db_config import DB_CONFIG

MAX_ATTEMPTS = 300
MAX_NEW_RECORDS = 200
MAX_RUNTIME_SECONDS = 1000


def _extract_entry_id(url: Optional[str]) -> Optional[int]:
    if not url:
        return None
    try:
        return int(url.rstrip("/").split("/")[-1])
    except (ValueError, IndexError):
        return None


def _read_last_scraped_id() -> Optional[int]:
    if os.path.exists(STATE_PATH):
        try:
            with open(STATE_PATH, "r") as f:
                value = f.read().strip()
                return int(value) if value else None
        except (OSError, ValueError):
            return None
    return None


def _write_last_scraped_id(value: int) -> None:
    os.makedirs(DB_DIR, exist_ok=True)
    with open(STATE_PATH, "w") as f:
        f.write(str(value))


def _infer_last_id_from_file() -> Optional[int]:
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


def _to_int(value):
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _to_float(value):
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalize_term(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    return value.strip().title()


def normalize_record(r):
    program = r.get("program")
    university = r.get("university")
    return {
        "program": program,
        "university": university,
        "term": _normalize_term(r.get("start_term")),
        "year": _to_int(r.get("start_year")),
        "status": r.get("applicant_status"),
        "us_or_international": r.get("citizenship"),
        "degree": r.get("degree_type"),
        "gpa": _to_float(r.get("gpa")),
        "gre": _to_float(r.get("gre_total")),
        "gre_v": _to_float(r.get("gre_verbal")),
        "gre_aw": _to_float(r.get("gre_aw")),
        "llm_generated_program": r.get("llm-generated-program") or program,
        "llm_generated_university": r.get("llm-generated-university") or university,
        "source_url": r.get("url"),
    }


def ensure_table(conn):
    with conn.cursor() as cur:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS applicants (
            p_id SERIAL PRIMARY KEY,
            program TEXT,
            university TEXT,
            term TEXT,
            year INTEGER,
            status TEXT,
            us_or_international TEXT,
            gpa FLOAT,
            gre FLOAT,
            gre_v FLOAT,
            gre_aw FLOAT,
            degree TEXT,
            llm_generated_program TEXT,
            llm_generated_university TEXT,
            source_url TEXT
        )
        """)
        cur.execute("ALTER TABLE applicants ADD COLUMN IF NOT EXISTS university TEXT")
        cur.execute("ALTER TABLE applicants ADD COLUMN IF NOT EXISTS year INTEGER")
        cur.execute("ALTER TABLE applicants ADD COLUMN IF NOT EXISTS us_or_international TEXT")
        cur.execute("ALTER TABLE applicants ADD COLUMN IF NOT EXISTS source_url TEXT")


def insert_new_records(conn, records):
    inserted = 0
    with conn.cursor() as cur:
        for r in records:
            url = r.get("source_url")
            if url:
                cur.execute("SELECT 1 FROM applicants WHERE source_url = %s", (url,))
                if cur.fetchone():
                    continue
            cur.execute("""
                INSERT INTO applicants (
                    program, university, term, year, status, us_or_international, gpa, gre, gre_v, gre_aw,
                    degree, llm_generated_program, llm_generated_university, source_url
                ) VALUES (
                    %(program)s, %(university)s, %(term)s, %(year)s, %(status)s, %(us_or_international)s, %(gpa)s, %(gre)s, %(gre_v)s, %(gre_aw)s,
                    %(degree)s, %(llm_generated_program)s, %(llm_generated_university)s, %(source_url)s
                )
            """, r)
            inserted += 1
    return inserted


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--lock", dest="lock_path", default=None)
    args = parser.parse_args()

    lock_path = args.lock_path
    status = "unknown"
    if lock_path:
        try:
            with open(lock_path, "w") as f:
                f.write(str(os.getpid()))
        except OSError:
            lock_path = None

    try:
        last_id = _read_last_scraped_id()
        if last_id is None:
            last_id = _infer_last_id_from_file()

        if last_id is None:
            last_id = 950000

        start_entry = last_id + 1
        end_entry = start_entry + MAX_ATTEMPTS

        raw_pages = []
        reached_max = False
        start_time = time.time()
        for page in scrape_data(start_entry, end_entry):
            raw_pages.append(page)
            if len(raw_pages) >= MAX_NEW_RECORDS:
                reached_max = True
                break
            if time.time() - start_time > MAX_RUNTIME_SECONDS:
                break

        if not raw_pages:
            print("No new pages found.")
            _write_last_scraped_id(end_entry - 1)
            status = "no_new_data"
            return

        cleaned = clean_data(raw_pages)
        normalized = [normalize_record(r) for r in cleaned]

        conn = psycopg.connect(**DB_CONFIG, autocommit=True)
        ensure_table(conn)
        inserted = insert_new_records(conn, normalized)
        conn.close()

        max_seen = max([_extract_entry_id(r.get("source_url")) for r in normalized if r.get("source_url")] or [last_id])
        _write_last_scraped_id(max_seen)

        print(f"Inserted {inserted} new records. Last scraped id: {max_seen}")
        status = "max_reached" if reached_max else "success"
    except Exception as e:
        status = "error"
        print(f"Pull failed: {e}")
    finally:
        try:
            os.makedirs(DB_DIR, exist_ok=True)
            with open(DONE_PATH, "w") as f:
                f.write(status)
        except OSError:
            pass
        if lock_path and os.path.exists(lock_path):
            try:
                os.remove(lock_path)
            except OSError:
                pass


if __name__ == "__main__":
    main()
