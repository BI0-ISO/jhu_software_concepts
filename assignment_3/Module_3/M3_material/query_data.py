"""
SQL query helpers for Module 3 analytics.

Each function opens a DB connection, runs a focused SQL query, and returns
simple numeric results used by the dashboard and PDF report.
"""
from db.db_config import DB_CONFIG
import psycopg

# Cohort definition:
# - Start term is Fall 2026, OR
# - Accepted applicants notified in 2026 (acceptance_date/date_added).
FALL_2026_TERM = "Fall 2026"
FALL_2026_START_DATE = "2026-01-01"
FALL_2026_END_DATE = "2026-12-31"

# -----------------------------
# Helper: Connect to DB
# -----------------------------
def get_connection():
    """Open a DB connection or raise a helpful error."""
    try:
        # Psycopg3 allows connection as a context manager
        conn = psycopg.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        raise RuntimeError(f"Error connecting to database: {e}") from e

def _term_filter(use_term_filter: bool):
    """Return SQL WHERE clause + params for the 2026 cohort or all entries."""
    if use_term_filter:
        # Include Fall 2026 start term entries OR accepted entries notified in 2026.
        return (
            "(term ILIKE %s OR (status ILIKE %s AND COALESCE(acceptance_date, date_added) BETWEEN %s AND %s))",
            [FALL_2026_TERM, "accept%", FALL_2026_START_DATE, FALL_2026_END_DATE],
        )
    return "TRUE", []

# -----------------------------
# 1. Count Fall 2026 entries
# -----------------------------
def count_total_applicants():
    """Total records in applicants table."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM applicants")
            return cur.fetchone()[0]

# -----------------------------
# 2. Count Fall 2026 entries
# -----------------------------
def count_fall_2026_entries(use_term_filter: bool):
    """Count entries in the 2026 cohort (or all entries if filter disabled)."""
    clause, params = _term_filter(use_term_filter)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(f"""
                SELECT COUNT(*) FROM applicants
                WHERE {clause}
            """, params)
            return cur.fetchone()[0]

# -----------------------------
# 3. Percent international students
# -----------------------------
def percent_international_students(use_term_filter: bool):
    """Percent international (not American/Other) in the selected cohort."""
    clause, params = _term_filter(use_term_filter)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(f"""
                SELECT COUNT(*) FROM applicants
                WHERE {clause} AND us_or_international NOT IN ('American', 'Other')
            """, params)
            intl_count = cur.fetchone()[0]

            cur.execute(f"SELECT COUNT(*) FROM applicants WHERE {clause}", params)
            total = cur.fetchone()[0]

            return round((intl_count / total) * 100, 2) if total else 0.0

# -----------------------------
# 4. Average metrics (GPA, GRE, GRE V, GRE AW)
# -----------------------------
def average_metrics_all_applicants(use_term_filter: bool):
    """Average GPA/GRE metrics for the selected cohort."""
    clause, params = _term_filter(use_term_filter)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(f"""
                SELECT 
                    AVG(gpa)::numeric(5,2),
                    AVG(gre)::numeric(5,2),
                    AVG(gre_v)::numeric(5,2),
                    AVG(gre_aw)::numeric(5,2)
                FROM applicants
                WHERE {clause}
                  AND (
                      gpa IS NOT NULL
                   OR gre IS NOT NULL
                   OR gre_v IS NOT NULL
                   OR gre_aw IS NOT NULL
                  )
            """, params)
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
def avg_gpa_american_fall_2026(use_term_filter: bool):
    """Average GPA for American applicants in the selected cohort."""
    clause, params = _term_filter(use_term_filter)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(f"""
                SELECT AVG(gpa)::numeric(5,2)
                FROM applicants
                WHERE {clause}
                  AND us_or_international='American'
                  AND gpa IS NOT NULL
            """, params)
            result = cur.fetchone()[0]
            return float(result) if result else None

# -----------------------------
# 6. Acceptance rate Fall 2026
# -----------------------------
def acceptance_rate_fall_2026(use_term_filter: bool):
    """Acceptance rate for the selected cohort."""
    accept_pattern = "accept%"
    clause, params = _term_filter(use_term_filter)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(f"""
                SELECT COUNT(*) FROM applicants
                WHERE {clause}
                  AND status ILIKE %s
            """, (*params, accept_pattern))
            acceptances = cur.fetchone()[0]

            cur.execute(f"""
                SELECT COUNT(*) FROM applicants
                WHERE {clause}
            """, params)
            total = cur.fetchone()[0]

            return round((acceptances / total) * 100, 2) if total else 0.0

# -----------------------------
# 7. Average GPA of Fall 2026 Acceptances
# -----------------------------
def avg_gpa_acceptances_fall_2026(use_term_filter: bool):
    """Average GPA among accepted applicants in the selected cohort."""
    accept_pattern = "accept%"
    clause, params = _term_filter(use_term_filter)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(f"""
                SELECT AVG(gpa)::numeric(5,2)
                FROM applicants
                WHERE {clause}
                  AND status ILIKE %s
                  AND gpa IS NOT NULL
            """, (*params, accept_pattern))
            result = cur.fetchone()[0]
            return float(result) if result else None

# -----------------------------
# 8. Count JHU Masters in CS applicants
# -----------------------------
def count_jhu_masters_cs(use_term_filter: bool):
    """Count JHU MS in CS applicants using LLM-normalized fields."""
    masters_pattern = "%Master%"
    cs_pattern = "%Computer Science%"
    clause, params = _term_filter(use_term_filter)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(f"""
                SELECT COUNT(*) FROM applicants
                WHERE {clause}
                  AND llm_generated_university IN ('Johns Hopkins University', 'JHU')
                  AND degree ILIKE %s
                  AND llm_generated_program ILIKE %s
            """, (*params, masters_pattern, cs_pattern))
            return cur.fetchone()[0]

# -----------------------------
# 9. Count Fall 2026 Acceptances for top PhD CS programs
#    using raw university names
# -----------------------------
def count_top_phd_acceptances_2026_raw_university(use_term_filter: bool):
    """Count accepted PhD CS applicants by raw university names in program."""
    top_unis = ['%Georgetown University%', '%MIT%', '%Stanford University%', '%Carnegie Mellon University%']
    accept_pattern = "accept%"
    cs_pattern = "%Computer Science%"
    clause, params = _term_filter(use_term_filter)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(f"""
                SELECT COUNT(*) FROM applicants
                WHERE {clause}
                  AND status ILIKE %s
                  AND degree ILIKE %s
                  AND llm_generated_program ILIKE %s
                  AND program ILIKE ANY(%s)
            """, (*params, accept_pattern, "%PhD%", cs_pattern, top_unis))
            return cur.fetchone()[0]

# -----------------------------
# 10. Count Fall 2026 Acceptances for top PhD CS programs
#    using LLM-generated university names
# -----------------------------
def count_top_phd_acceptances_2026_llm(use_term_filter: bool):
    """Count accepted PhD CS applicants using LLM-normalized universities."""
    top_unis = ['Georgetown University', 'MIT', 'Stanford University', 'Carnegie Mellon University']
    accept_pattern = "accept%"
    cs_pattern = "%Computer Science%"
    clause, params = _term_filter(use_term_filter)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(f"""
                SELECT COUNT(*) FROM applicants
                WHERE {clause}
                  AND status ILIKE %s
                  AND degree ILIKE %s
                  AND llm_generated_program ILIKE %s
                  AND llm_generated_university = ANY(%s)
            """, (*params, accept_pattern, "%PhD%", cs_pattern, top_unis))
            return cur.fetchone()[0]

# -----------------------------
# 11. Additional example queries
# -----------------------------
def additional_question_1(use_term_filter: bool):
    """Percent of applicants who reported a GPA."""
    clause, params = _term_filter(use_term_filter)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) FROM applicants WHERE {clause}", params)
            total = cur.fetchone()[0]
            cur.execute(f"SELECT COUNT(*) FROM applicants WHERE {clause} AND gpa IS NOT NULL", params)
            with_gpa = cur.fetchone()[0]
            return round((with_gpa / total) * 100, 2) if total else 0.0

def additional_question_2(use_term_filter: bool):
    """Average GRE Quant for international applicants."""
    clause, params = _term_filter(use_term_filter)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(f"""
                SELECT AVG(gre)::numeric(5,2)
                FROM applicants
                WHERE {clause}
                  AND us_or_international NOT IN ('American','Other')
                  AND gre IS NOT NULL
            """, params)
            result = cur.fetchone()[0]
            return float(result) if result else None
