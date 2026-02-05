import json
import psycopg
from db_config import DB_CONFIG

DATA_PATH = "data/cleaned_grad_cafe.json"


def create_table(conn):
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS applicants (
                p_id INTEGER PRIMARY KEY,
                program TEXT,
                comments TEXT,
                date_added DATE,
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
                llm_generated_university TEXT
            );
        """)
        conn.commit()


def load_json():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def transform_record(raw, p_id):
    """Map module-2 JSON fields to assignment schema"""

    term = None
    if raw.get("start_term") and raw.get("start_year"):
        term = f"{raw['start_term']} {raw['start_year']}"

    return {
        "p_id": p_id,
        "program": raw.get("program"),
        "comments": raw.get("comments"),
        "date_added": raw.get("date_added"),
        "url": raw.get("url"),
        "status": raw.get("applicant_status"),
        "term": term,
        "us_or_international": raw.get("citizenship"),
        "gpa": raw.get("gpa"),
        "gre": raw.get("gre_total"),
        "gre_v": raw.get("gre_verbal"),
        "gre_aw": raw.get("gre_aw"),
        "degree": raw.get("degree_type"),
        "llm_generated_program": raw.get("llm_generated_program"),
        "llm_generated_university": raw.get("llm_generated_university"),
    }


def insert_data(conn, raw_records):
    with conn.cursor() as cur:
        for i, raw in enumerate(raw_records, start=1):
            record = transform_record(raw, i)

            cur.execute("""
                INSERT INTO applicants (
                    p_id, program, comments, date_added, url, status,
                    term, us_or_international, gpa, gre, gre_v, gre_aw,
                    degree, llm_generated_program, llm_generated_university
                ) VALUES (
                    %(p_id)s, %(program)s, %(comments)s, %(date_added)s, %(url)s, %(status)s,
                    %(term)s, %(us_or_international)s, %(gpa)s, %(gre)s, %(gre_v)s, %(gre_aw)s,
                    %(degree)s, %(llm_generated_program)s, %(llm_generated_university)s
                )
                ON CONFLICT (p_id) DO NOTHING;
            """, record)

        conn.commit()


def main():
    conn = psycopg.connect(**DB_CONFIG)

    create_table(conn)

    raw_records = load_json()
    insert_data(conn, raw_records)

    conn.close()
    print("✅ Data successfully loaded into PostgreSQL.")


if __name__ == "__main__":
    main()
