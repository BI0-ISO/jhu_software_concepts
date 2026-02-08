import json
from datetime import datetime, date
import psycopg
from db_config import DB_CONFIG

def load_records(path):
    with open(path, "r") as f:
        # Detect JSON array vs JSONL by first non-whitespace char
        first = ""
        while True:
            ch = f.read(1)
            if not ch:
                break
            if not ch.isspace():
                first = ch
                break
        f.seek(0)

        if first == "[":
            return json.load(f)

        records = []
        for line in f:
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))
        return records

def to_int(value):
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None

def to_float(value):
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None

def to_date(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    text = str(value).strip()
    if not text:
        return None
    if len(text) >= 10 and text[:10].count("-") == 2 and text[:10][:4].isdigit():
        return text[:10]
    for fmt in (
        "%d/%m/%Y",
        "%m/%d/%Y",
        "%b %d, %Y",
        "%B %d, %Y",
        "%b %d %Y",
        "%B %d %Y",
        "%d %b %Y",
        "%d %B %Y",
    ):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    return None

def combine_program_university(program, university):
    if program and university and university not in program:
        return f"{university} - {program}"
    return program or university

def normalize_record(r):
    university = r.get("university")
    program = r.get("program")
    status = r.get("applicant_status")
    term = r.get("start_term") if status == "accepted" else None
    return {
        "program": combine_program_university(program, university),
        "comments": r.get("comments"),
        "date_added": to_date(r.get("date_added")),
        "acceptance_date": to_date(r.get("acceptance_date")),
        "url": r.get("url"),
        "university": university,
        "term": term,
        "year": to_int(r.get("start_year")),
        "status": status,
        "us_or_international": r.get("citizenship"),
        "degree": r.get("degree_type"),
        "gpa": to_float(r.get("gpa")),
        "gre": to_float(r.get("gre_total")),
        "gre_v": to_float(r.get("gre_verbal")),
        "gre_aw": to_float(r.get("gre_aw")),
        "llm_generated_program": r.get("llm-generated-program"),
        "llm_generated_university": r.get("llm-generated-university"),
    }

def create_table(conn):
    with conn.cursor() as cur:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS applicants (
            p_id SERIAL PRIMARY KEY,
            program TEXT,
            comments TEXT,
            date_added DATE,
            acceptance_date DATE,
            url TEXT,
            status TEXT,
            term TEXT,
            us_or_international TEXT,
            gpa FLOAT,
            gre FLOAT,
            gre_v FLOAT,
            gre_aw FLOAT,
            degree TEXT,
            llm_generated_program TEXT,
            llm_generated_university TEXT,
            university TEXT,
            year INTEGER
        )
        """)
        # Ensure required columns exist if table was created with an older schema
        cur.execute("ALTER TABLE applicants ADD COLUMN IF NOT EXISTS comments TEXT")
        cur.execute("ALTER TABLE applicants ADD COLUMN IF NOT EXISTS date_added DATE")
        cur.execute("ALTER TABLE applicants ADD COLUMN IF NOT EXISTS acceptance_date DATE")
        cur.execute("ALTER TABLE applicants ADD COLUMN IF NOT EXISTS url TEXT")
        cur.execute("ALTER TABLE applicants ADD COLUMN IF NOT EXISTS university TEXT")
        cur.execute("ALTER TABLE applicants ADD COLUMN IF NOT EXISTS year INTEGER")
        cur.execute("ALTER TABLE applicants ADD COLUMN IF NOT EXISTS us_or_international TEXT")
    print("Table 'applicants' ready.")

def insert_data(conn, records):
    with conn.cursor() as cur:
        for r in records:
            try:
                cur.execute("""
                    INSERT INTO applicants (
                        program, comments, date_added, acceptance_date, url, status, term, us_or_international, gpa, gre, gre_v, gre_aw,
                        degree, llm_generated_program, llm_generated_university, university, year
                    ) VALUES (
                        %(program)s, %(comments)s, %(date_added)s, %(acceptance_date)s, %(url)s, %(status)s, %(term)s, %(us_or_international)s, %(gpa)s, %(gre)s, %(gre_v)s, %(gre_aw)s,
                        %(degree)s, %(llm_generated_program)s, %(llm_generated_university)s, %(university)s, %(year)s
                    )
                """, r)
            except Exception as e:
                print(f"Error inserting record: {e}")

def main():
    conn = psycopg.connect(**DB_CONFIG, autocommit=True)
    create_table(conn)
    raw_records = load_records("M3_material/data/llm_extend_applicant_data.json")
    records = [normalize_record(r) for r in raw_records]
    insert_data(conn, records)
    conn.close()
    print("Data load complete.")

if __name__ == "__main__":
    main()
