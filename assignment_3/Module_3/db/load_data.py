import json
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

def normalize_record(r):
    return {
        "program": r.get("program"),
        "university": r.get("university"),
        "term": r.get("start_term"),
        "year": to_int(r.get("start_year")),
        "status": r.get("applicant_status"),
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
            llm_generated_university TEXT
        )
        """)
        # Ensure required columns exist if table was created with an older schema
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
                        program, university, term, year, status, us_or_international, gpa, gre, gre_v, gre_aw,
                        degree, llm_generated_program, llm_generated_university
                    ) VALUES (
                        %(program)s, %(university)s, %(term)s, %(year)s, %(status)s, %(us_or_international)s, %(gpa)s, %(gre)s, %(gre_v)s, %(gre_aw)s,
                        %(degree)s, %(llm_generated_program)s, %(llm_generated_university)s
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
