"""
SQL query helpers for Module 3 analytics.

Each function opens a DB connection, runs a focused SQL query, and returns
simple numeric results used by the dashboard and PDF report.
"""
import psycopg
from psycopg import sql

from db.db_config import get_db_config
# Cohort definition:
# - Start term is Fall (term column stores only the semester word),
#   and the entry was added in 2026, OR
# - Accepted applicants notified in 2026 (acceptance_date/date_added).
FALL_TERM = "Fall"
YEAR_START = "2026-01-01"
YEAR_END = "2026-12-31"
MAX_LIMIT = 100

# -----------------------------
# Helper: Connect to DB
# -----------------------------
def get_connection():
    """Open a DB connection or raise a helpful error."""
    try:
        # Psycopg3 allows connection as a context manager
        conn = psycopg.connect(**get_db_config())
        return conn
    except Exception as exc:
        raise RuntimeError(f"Error connecting to database: {exc}") from exc

def _clamp_limit(value: int | None, default: int = 1) -> int:
    """Clamp limit values to a safe 1..MAX_LIMIT range."""
    try:
        limit_value = int(value) if value is not None else default
    except (TypeError, ValueError):
        limit_value = default
    if limit_value < 1:
        return 1
    if limit_value > MAX_LIMIT:
        return MAX_LIMIT
    return limit_value


def _term_filter(use_term_filter: bool):
    """Return SQL WHERE clause + params for the 2026 cohort or all entries."""
    if use_term_filter:
        # Include Fall entries added in 2026 OR accepted entries notified in 2026.
        return (
            "((term ILIKE %s AND date_added BETWEEN %s AND %s) "
            "OR (status ILIKE %s AND COALESCE(acceptance_date, date_added) "
            "BETWEEN %s AND %s))",
            [FALL_TERM, YEAR_START, YEAR_END, "accept%", YEAR_START, YEAR_END],
        )
    return "TRUE", []

# -----------------------------
# 1. Count 2026 cohort entries
# -----------------------------
def count_total_applicants():
    """Total records in applicants table."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            limit_value = _clamp_limit(None)
            stmt = sql.SQL(
                "SELECT COUNT(*) FROM applicants LIMIT {limit}"
            ).format(limit=sql.Placeholder())
            cur.execute(stmt, [limit_value])
            return cur.fetchone()[0]

# -----------------------------
# 2. Count 2026 cohort entries
# -----------------------------
def count_fall_2026_entries(use_term_filter: bool):
    """Count entries in the 2026 cohort (or all entries if filter disabled)."""
    clause, params = _term_filter(use_term_filter)
    clause_sql = sql.SQL(clause)
    with get_connection() as conn:
        with conn.cursor() as cur:
            limit_value = _clamp_limit(None)
            stmt = sql.SQL(
                "SELECT COUNT(*) FROM applicants WHERE {clause} LIMIT {limit}"
            ).format(clause=clause_sql, limit=sql.Placeholder())
            cur.execute(stmt, params + [limit_value])
            return cur.fetchone()[0]

# -----------------------------
# 3. Percent international students
# -----------------------------
def percent_international_students(use_term_filter: bool):
    """Percent international (not American/Other) in the selected cohort."""
    clause, params = _term_filter(use_term_filter)
    clause_sql = sql.SQL(clause)
    with get_connection() as conn:
        with conn.cursor() as cur:
            limit_value = _clamp_limit(None)
            stmt = sql.SQL(
                "SELECT COUNT(*) FROM applicants "
                "WHERE {clause} AND us_or_international NOT IN ('American', 'Other') "
                "LIMIT {limit}"
            ).format(clause=clause_sql, limit=sql.Placeholder())
            cur.execute(stmt, params + [limit_value])
            intl_count = cur.fetchone()[0]

            stmt = sql.SQL(
                "SELECT COUNT(*) FROM applicants WHERE {clause} LIMIT {limit}"
            ).format(clause=clause_sql, limit=sql.Placeholder())
            cur.execute(stmt, params + [limit_value])
            total = cur.fetchone()[0]

            return round((intl_count / total) * 100, 2) if total else 0.0

# -----------------------------
# 4. Average metrics (GPA, GRE, GRE V, GRE AW)
# -----------------------------
def average_metrics_all_applicants(use_term_filter: bool):
    """Average GPA/GRE metrics for the selected cohort."""
    clause, params = _term_filter(use_term_filter)
    clause_sql = sql.SQL(clause)
    with get_connection() as conn:
        with conn.cursor() as cur:
            limit_value = _clamp_limit(None)
            stmt = sql.SQL(
                "SELECT "
                "AVG(gpa)::numeric(5,2), "
                "AVG(gre)::numeric(5,2), "
                "AVG(gre_v)::numeric(5,2), "
                "AVG(gre_aw)::numeric(5,2) "
                "FROM applicants "
                "WHERE {clause} "
                "  AND ("
                "      gpa IS NOT NULL "
                "   OR gre IS NOT NULL "
                "   OR gre_v IS NOT NULL "
                "   OR gre_aw IS NOT NULL "
                "  ) "
                "LIMIT {limit}"
            ).format(clause=clause_sql, limit=sql.Placeholder())
            cur.execute(stmt, params + [limit_value])
            row = cur.fetchone()
            return {
                "avg_gpa": float(row[0]) if row[0] else None,
                "avg_gre": float(row[1]) if row[1] else None,
                "avg_gre_v": float(row[2]) if row[2] else None,
                "avg_gre_aw": float(row[3]) if row[3] else None
            }

# -----------------------------
# 5. Average GPA of American 2026 cohort applicants
# -----------------------------
def avg_gpa_american_fall_2026(use_term_filter: bool):
    """Average GPA for American applicants in the selected cohort."""
    clause, params = _term_filter(use_term_filter)
    clause_sql = sql.SQL(clause)
    with get_connection() as conn:
        with conn.cursor() as cur:
            limit_value = _clamp_limit(None)
            stmt = sql.SQL(
                "SELECT AVG(gpa)::numeric(5,2) "
                "FROM applicants "
                "WHERE {clause} "
                "  AND us_or_international='American' "
                "  AND gpa IS NOT NULL "
                "LIMIT {limit}"
            ).format(clause=clause_sql, limit=sql.Placeholder())
            cur.execute(stmt, params + [limit_value])
            result = cur.fetchone()[0]
            return float(result) if result else None

# -----------------------------
# 6. Acceptance rate (2026 cohort)
# -----------------------------
def acceptance_rate_fall_2026(use_term_filter: bool):
    """Acceptance rate for the selected cohort."""
    accept_pattern = "accept%"
    clause, params = _term_filter(use_term_filter)
    clause_sql = sql.SQL(clause)
    with get_connection() as conn:
        with conn.cursor() as cur:
            limit_value = _clamp_limit(None)
            stmt = sql.SQL(
                "SELECT COUNT(*) FROM applicants "
                "WHERE {clause} "
                "  AND status ILIKE %s "
                "LIMIT {limit}"
            ).format(clause=clause_sql, limit=sql.Placeholder())
            cur.execute(stmt, (*params, accept_pattern, limit_value))
            acceptances = cur.fetchone()[0]

            stmt = sql.SQL(
                "SELECT COUNT(*) FROM applicants WHERE {clause} LIMIT {limit}"
            ).format(clause=clause_sql, limit=sql.Placeholder())
            cur.execute(stmt, params + [limit_value])
            total = cur.fetchone()[0]

            return round((acceptances / total) * 100, 2) if total else 0.0

# -----------------------------
# 7. Average GPA of 2026 cohort acceptances
# -----------------------------
def avg_gpa_acceptances_fall_2026(use_term_filter: bool):
    """Average GPA among accepted applicants in the selected cohort."""
    accept_pattern = "accept%"
    clause, params = _term_filter(use_term_filter)
    clause_sql = sql.SQL(clause)
    with get_connection() as conn:
        with conn.cursor() as cur:
            limit_value = _clamp_limit(None)
            stmt = sql.SQL(
                "SELECT AVG(gpa)::numeric(5,2) "
                "FROM applicants "
                "WHERE {clause} "
                "  AND status ILIKE %s "
                "  AND gpa IS NOT NULL "
                "LIMIT {limit}"
            ).format(clause=clause_sql, limit=sql.Placeholder())
            cur.execute(stmt, (*params, accept_pattern, limit_value))
            result = cur.fetchone()[0]
            return float(result) if result else None

# -----------------------------
# 8. Count JHU Masters in CS applicants
# -----------------------------
def count_jhu_masters_cs(use_term_filter: bool):
    """Count JHU MS in CS applicants using LLM + raw text edge cases."""
    masters_pattern = "%Master%"
    cs_pattern = "%Computer Science%"
    # Cover common variants and misspellings in raw text.
    uni_patterns = [
        "%Johns Hopkins University%",
        "%Johns Hopkins Univ%",
        "%John Hopkins%",
        "%Johns Hopkins%",
        "%John Hopkins University%",
        "%Johns Hopkins Univeristy%",
        "%JHU%",
    ]
    clause, params = _term_filter(use_term_filter)
    clause_sql = sql.SQL(clause)
    with get_connection() as conn:
        with conn.cursor() as cur:
            limit_value = _clamp_limit(None)
            stmt = sql.SQL(
                "SELECT COUNT(*) FROM applicants "
                "WHERE {clause} "
                "  AND degree ILIKE %s "
                "  AND llm_generated_program ILIKE %s "
                "  AND ("
                "        llm_generated_university ILIKE ANY(%s) "
                "     OR program ILIKE ANY(%s)"
                "  ) "
                "LIMIT {limit}"
            ).format(clause=clause_sql, limit=sql.Placeholder())
            cur.execute(
                stmt,
                (*params, masters_pattern, cs_pattern, uni_patterns, uni_patterns, limit_value),
            )
            return cur.fetchone()[0]

# -----------------------------
# 9. Count 2026 cohort acceptances for top PhD CS programs
#    using raw university names
# -----------------------------
def count_top_phd_acceptances_2026_raw_university(use_term_filter: bool):
    """Count accepted PhD CS applicants by raw university names in program."""
    top_unis = [
        "%Georgetown University%",
        "%MIT%",
        "%Stanford University%",
        "%Carnegie Mellon University%",
    ]
    accept_pattern = "accept%"
    cs_pattern = "%Computer Science%"
    clause, params = _term_filter(use_term_filter)
    clause_sql = sql.SQL(clause)
    with get_connection() as conn:
        with conn.cursor() as cur:
            limit_value = _clamp_limit(None)
            stmt = sql.SQL(
                "SELECT COUNT(*) FROM applicants "
                "WHERE {clause} "
                "  AND status ILIKE %s "
                "  AND degree ILIKE %s "
                "  AND llm_generated_program ILIKE %s "
                "  AND program ILIKE ANY(%s) "
                "LIMIT {limit}"
            ).format(clause=clause_sql, limit=sql.Placeholder())
            cur.execute(
                stmt,
                (*params, accept_pattern, "%PhD%", cs_pattern, top_unis, limit_value),
            )
            return cur.fetchone()[0]

# -----------------------------
# 10. Count 2026 cohort acceptances for top PhD CS programs
#     using LLM-generated university names
# -----------------------------
def count_top_phd_acceptances_2026_llm(use_term_filter: bool):
    """Count accepted PhD CS applicants using LLM-normalized universities."""
    top_unis = [
        "Georgetown University",
        "MIT",
        "Stanford University",
        "Carnegie Mellon University",
    ]
    accept_pattern = "accept%"
    cs_pattern = "%Computer Science%"
    clause, params = _term_filter(use_term_filter)
    clause_sql = sql.SQL(clause)
    with get_connection() as conn:
        with conn.cursor() as cur:
            limit_value = _clamp_limit(None)
            stmt = sql.SQL(
                "SELECT COUNT(*) FROM applicants "
                "WHERE {clause} "
                "  AND status ILIKE %s "
                "  AND degree ILIKE %s "
                "  AND llm_generated_program ILIKE %s "
                "  AND llm_generated_university = ANY(%s) "
                "LIMIT {limit}"
            ).format(clause=clause_sql, limit=sql.Placeholder())
            cur.execute(
                stmt,
                (*params, accept_pattern, "%PhD%", cs_pattern, top_unis, limit_value),
            )
            return cur.fetchone()[0]

# -----------------------------
# 11. Additional example queries
# -----------------------------
def additional_question_1(use_term_filter: bool):
    """Percent of applicants who reported a GPA."""
    clause, params = _term_filter(use_term_filter)
    clause_sql = sql.SQL(clause)
    with get_connection() as conn:
        with conn.cursor() as cur:
            limit_value = _clamp_limit(None)
            stmt = sql.SQL(
                "SELECT COUNT(*) FROM applicants WHERE {clause} LIMIT {limit}"
            ).format(clause=clause_sql, limit=sql.Placeholder())
            cur.execute(stmt, params + [limit_value])
            total = cur.fetchone()[0]
            stmt = sql.SQL(
                "SELECT COUNT(*) FROM applicants "
                "WHERE {clause} AND gpa IS NOT NULL "
                "LIMIT {limit}"
            ).format(clause=clause_sql, limit=sql.Placeholder())
            cur.execute(stmt, params + [limit_value])
            with_gpa = cur.fetchone()[0]
            return round((with_gpa / total) * 100, 2) if total else 0.0

def additional_question_2(use_term_filter: bool):
    """Average GRE Quant for international applicants."""
    clause, params = _term_filter(use_term_filter)
    clause_sql = sql.SQL(clause)
    with get_connection() as conn:
        with conn.cursor() as cur:
            limit_value = _clamp_limit(None)
            stmt = sql.SQL(
                "SELECT AVG(gre)::numeric(5,2) "
                "FROM applicants "
                "WHERE {clause} "
                "  AND us_or_international NOT IN ('American','Other') "
                "  AND gre IS NOT NULL "
                "LIMIT {limit}"
            ).format(clause=clause_sql, limit=sql.Placeholder())
            cur.execute(stmt, params + [limit_value])
            result = cur.fetchone()[0]
            return float(result) if result else None


def get_latest_db_id():
    """Return the highest GradCafe result ID stored in the database."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            limit_value = _clamp_limit(None)
            stmt = sql.SQL(
                "SELECT MAX(SUBSTRING(url FROM '/(\\d+)$')::int) "
                "FROM applicants WHERE url ~ '/\\d+$' "
                "LIMIT {limit}"
            ).format(limit=sql.Placeholder())
            cur.execute(stmt, [limit_value])
            value = cur.fetchone()[0]
            return int(value) if value is not None else None


def build_analysis_results():
    """Return the analysis dict used by the Module 3 dashboard."""
    return {
        "total_applicants": count_total_applicants(),
        "year_2026": {
            "fall_2026_count": count_fall_2026_entries(True),
            "percent_international": percent_international_students(True),
            "average_metrics": average_metrics_all_applicants(True),
            "avg_gpa_american_fall_2026": avg_gpa_american_fall_2026(True),
            "acceptance_rate_fall_2026": acceptance_rate_fall_2026(True),
            "avg_gpa_acceptances_fall_2026": avg_gpa_acceptances_fall_2026(True),
            "jhu_masters_cs": count_jhu_masters_cs(True),
            "top_phd_acceptances_2026_raw": count_top_phd_acceptances_2026_raw_university(True),
            "top_phd_acceptances_2026_llm": count_top_phd_acceptances_2026_llm(True),
            "additional_question_1": additional_question_1(True),
            "additional_question_2": additional_question_2(True),
        },
        "all_time": {
            "total_entries": count_total_applicants(),
            "percent_international": percent_international_students(False),
            "average_metrics": average_metrics_all_applicants(False),
            "avg_gpa_american_fall_2026": avg_gpa_american_fall_2026(False),
            "acceptance_rate_fall_2026": acceptance_rate_fall_2026(False),
            "avg_gpa_acceptances_fall_2026": avg_gpa_acceptances_fall_2026(False),
            "jhu_masters_cs": count_jhu_masters_cs(False),
            "top_phd_acceptances_2026_raw": count_top_phd_acceptances_2026_raw_university(False),
            "top_phd_acceptances_2026_llm": count_top_phd_acceptances_2026_llm(False),
            "additional_question_1": additional_question_1(False),
            "additional_question_2": additional_question_2(False),
        },
    }
