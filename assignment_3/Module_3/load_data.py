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

def insert_data(conn, records):
    with conn.cursor() as cur:
        for r in records:
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
            """, r)
        conn.commit()

def main():
    conn = psycopg.connect(**DB_CONFIG)
    create_table(conn)

    records = load_json()
    insert_data(conn, records)

    conn.close()
    print("Data successfully loaded.")

if __name__ == "__main__":
    main()
