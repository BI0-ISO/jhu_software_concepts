import os
import json
from datetime import datetime
import psycopg

# Load database config from .env
from dotenv import load_dotenv
load_dotenv()

DB_CONFIG = {
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
}

# Helper function to parse dates in DD/MM/YYYY format
def parse_date(date_str):
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%d/%m/%Y").date()
    except ValueError:
        return None

# Load JSON Lines from data folder
def load_json():
    records = []
    json_path = os.path.join(os.path.dirname(__file__), "data", "llm_extend_applicant_data.json")
    with open(json_path, "r") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
    return records

# Create the PostgreSQL table
def create_table(conn):
    with conn.cursor() as cur:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS applicants (
            p_id SERIAL PRIMARY KEY,
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
    print("✅ Table 'applicants' ready.")

# Insert data into PostgreSQL
def insert_data(conn, records):
    with conn.cursor() as cur:
        for idx, rec in enumerate(records, start=1):
            record = {
                "p_id": idx,
                "program": rec.get("program"),
                "comments": rec.get("comments"),
                "date_added": parse_date(rec.get("date_added")),
                "url": rec.get("url"),
                "status": rec.get("applicant_status"),
                "term": f"{rec.get('start_term')} {rec.get('start_year')}" if rec.get("start_term") else None,
                "us_or_international": rec.get("citizenship"),
                "gpa": rec.get("gpa"),
                "gre": rec.get("gre_total"),
                "gre_v": rec.get("gre_verbal"),
                "gre_aw": rec.get("gre_aw"),
                "degree": rec.get("degree_type"),
                "llm_generated_program": rec.get("llm_generated_program"),
                "llm_generated_university": rec.get("llm_generated_university"),
            }

            cur.execute("""
            INSERT INTO applicants (
                p_id, program, comments, date_added, url, status, term,
                us_or_international, gpa, gre, gre_v, gre_aw, degree,
                llm_generated_program, llm_generated_university
            ) VALUES (
                %(p_id)s, %(program)s, %(comments)s, %(date_added)s, %(url)s, %(status)s, %(term)s,
                %(us_or_international)s, %(gpa)s, %(gre)s, %(gre_v)s, %(gre_aw)s, %(degree)s,
                %(llm_generated_program)s, %(llm_generated_university)s
            )
            ON CONFLICT (p_id) DO NOTHING;
            """, record)
        conn.commit()
    print(f"✅ Inserted {len(records)} records into 'applicants'.")

# Main function
def main():
    records = load_json()
    with psycopg.connect(**DB_CONFIG) as conn:
        create_table(conn)
        insert_data(conn, records)

if __name__ == "__main__":
    main()
