# M3_material/query_data.py
from db.db_config import DB_CONFIG
import psycopg

# -----------------------------
# Helper: Connect to DB
# -----------------------------
def get_connection():
    try:
        # Psycopg3 allows connection as a context manager
        conn = psycopg.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        raise RuntimeError(f"Error connecting to database: {e}") from e

# -----------------------------
# 1. Count Fall 2026 entries
# -----------------------------
def count_total_applicants():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM applicants")
            return cur.fetchone()[0]

# -----------------------------
# 2. Count Fall 2026 entries
# -----------------------------
def count_fall_2026_entries():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) FROM applicants
                WHERE term = 'Fall' AND year = 2026
            """)
            return cur.fetchone()[0]

# -----------------------------
# 3. Percent international students
# -----------------------------
def percent_international_students():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) FROM applicants
                WHERE us_or_international NOT IN ('American', 'Other')
            """)
            intl_count = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM applicants")
            total = cur.fetchone()[0]

            return round((intl_count / total) * 100, 2) if total else 0.0

# -----------------------------
# 4. Average metrics (GPA, GRE, GRE V, GRE AW)
# -----------------------------
def average_metrics_all_applicants():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    AVG(gpa)::numeric(5,2),
                    AVG(gre)::numeric(5,2),
                    AVG(gre_v)::numeric(5,2),
                    AVG(gre_aw)::numeric(5,2)
                FROM applicants
                WHERE gpa IS NOT NULL
                   OR gre IS NOT NULL
                   OR gre_v IS NOT NULL
                   OR gre_aw IS NOT NULL
            """)
            row = cur.fetchone()
            return {
                "avg_gpa": float(row[0]) if row[0] else None,
                "avg_gre": float(row[1]) if row[1] else None,
                "avg_gre_v": float(row[2]) if row[2] else None,
                "avg_gre_aw": float(row[3]) if row[3] else None
            }

# -----------------------------
# 5. Average GPA of American Fall 2026 applicants
# -----------------------------
def avg_gpa_american_fall_2026():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT AVG(gpa)::numeric(5,2)
                FROM applicants
                WHERE term='Fall' AND year=2026 AND us_or_international='American'
                  AND gpa IS NOT NULL
            """)
            result = cur.fetchone()[0]
            return float(result) if result else None

# -----------------------------
# 6. Acceptance rate Fall 2026
# -----------------------------
def acceptance_rate_fall_2026():
    accept_pattern = "accept%"
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) FROM applicants
                WHERE term='Fall' AND year=2026 AND status ILIKE %s
            """, (accept_pattern,))
            acceptances = cur.fetchone()[0]

            cur.execute("""
                SELECT COUNT(*) FROM applicants
                WHERE term='Fall' AND year=2026
            """)
            total = cur.fetchone()[0]

            return round((acceptances / total) * 100, 2) if total else 0.0

# -----------------------------
# 7. Average GPA of Fall 2026 Acceptances
# -----------------------------
def avg_gpa_acceptances_fall_2026():
    accept_pattern = "accept%"
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT AVG(gpa)::numeric(5,2)
                FROM applicants
                WHERE term='Fall' AND year=2026 AND status ILIKE %s
                  AND gpa IS NOT NULL
            """, (accept_pattern,))
            result = cur.fetchone()[0]
            return float(result) if result else None

# -----------------------------
# 8. Count JHU Masters in CS applicants
# -----------------------------
def count_jhu_masters_cs():
    masters_pattern = "%Master%"
    cs_pattern = "%Computer Science%"
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) FROM applicants
                WHERE llm_generated_university IN ('Johns Hopkins University', 'JHU')
                  AND degree ILIKE %s
                  AND llm_generated_program ILIKE %s
            """, (masters_pattern, cs_pattern))
            return cur.fetchone()[0]

# -----------------------------
# 9. Count Fall 2026 Acceptances for top PhD CS programs
#    using raw university names
# -----------------------------
def count_top_phd_acceptances_2026_raw_university():
    top_unis = ['Georgetown University', 'MIT', 'Stanford University', 'Carnegie Mellon University']
    accept_pattern = "accept%"
    phd_pattern = "%PhD%"
    cs_pattern = "%Computer Science%"
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) FROM applicants
                WHERE year=2026
                  AND status ILIKE %s
                  AND llm_generated_program ILIKE %s
                  AND llm_generated_program ILIKE %s
                  AND university = ANY(%s)
            """, (accept_pattern, phd_pattern, cs_pattern, top_unis))
            return cur.fetchone()[0]

# -----------------------------
# 10. Count Fall 2026 Acceptances for top PhD CS programs
#    using LLM-generated university names
# -----------------------------
def count_top_phd_acceptances_2026_llm():
    top_unis = ['Georgetown University', 'MIT', 'Stanford University', 'Carnegie Mellon University']
    accept_pattern = "accept%"
    phd_pattern = "%PhD%"
    cs_pattern = "%Computer Science%"
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) FROM applicants
                WHERE year=2026
                  AND status ILIKE %s
                  AND llm_generated_program ILIKE %s
                  AND llm_generated_program ILIKE %s
                  AND llm_generated_university = ANY(%s)
            """, (accept_pattern, phd_pattern, cs_pattern, top_unis))
            return cur.fetchone()[0]

# -----------------------------
# 11. Additional example queries
# -----------------------------
def additional_question_1():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) FROM applicants
                WHERE term='Fall' AND year=2026 AND us_or_international NOT IN ('American','Other')
            """)
            return cur.fetchone()[0]

def additional_question_2():
    phd_pattern = "%PhD%"
    cs_pattern = "%Computer Science%"
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT AVG(gre)::numeric(5,2)
                FROM applicants
                WHERE term='Fall' AND year=2026
                  AND llm_generated_program ILIKE %s
                  AND llm_generated_program ILIKE %s
                  AND gre IS NOT NULL
            """, (phd_pattern, cs_pattern))
            result = cur.fetchone()[0]
            return float(result) if result else None
