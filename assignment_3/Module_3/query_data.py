import os
import psycopg
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
}

def run_query(query, fetchone=False):
    with psycopg.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            if fetchone:
                return cur.fetchone()[0]
            return cur.fetchall()

# --------------------------------------------------
# QUESTION 1
# --------------------------------------------------
def count_fall_2026_entries():
    return run_query("""
        SELECT COUNT(*)
        FROM applicants
        WHERE term = 'Fall 2026';
    """, fetchone=True)

# --------------------------------------------------
# QUESTION 2
# --------------------------------------------------
def percent_international_students():
    return run_query("""
        SELECT ROUND(
            (100.0 * SUM(CASE WHEN us_or_international = 'International' THEN 1 ELSE 0 END)
            / COUNT(*))::numeric, 2
        )
        FROM applicants;
    """, fetchone=True)

# --------------------------------------------------
# QUESTION 3
# --------------------------------------------------
def average_metrics_all_applicants():
    return run_query("""
        SELECT
            ROUND(AVG(gpa)::numeric, 2),
            ROUND(AVG(gre)::numeric, 2),
            ROUND(AVG(gre_v)::numeric, 2),
            ROUND(AVG(gre_aw)::numeric, 2)
        FROM applicants
        WHERE gpa IS NOT NULL
           OR gre IS NOT NULL
           OR gre_v IS NOT NULL
           OR gre_aw IS NOT NULL;
    """)[0]

# --------------------------------------------------
# QUESTION 4
# --------------------------------------------------
def avg_gpa_american_fall_2026():
    return run_query("""
        SELECT ROUND(AVG(gpa)::numeric, 2)
        FROM applicants
        WHERE us_or_international = 'American'
          AND term = 'Fall 2026'
          AND gpa IS NOT NULL;
    """, fetchone=True)

# --------------------------------------------------
# QUESTION 5
# --------------------------------------------------
def percent_acceptances_fall_2026():
    return run_query("""
        SELECT ROUND(
            (100.0 * SUM(CASE WHEN status = 'accepted' THEN 1 ELSE 0 END)
            / COUNT(*))::numeric, 2
        )
        FROM applicants
        WHERE term = 'Fall 2026';
    """, fetchone=True)

# --------------------------------------------------
# QUESTION 6
# --------------------------------------------------
def avg_gpa_accepted_fall_2026():
    return run_query("""
        SELECT ROUND(AVG(gpa)::numeric, 2)
        FROM applicants
        WHERE term = 'Fall 2026'
          AND status = 'accepted'
          AND gpa IS NOT NULL;
    """, fetchone=True)

# --------------------------------------------------
# QUESTION 7 (JHU / CS / Masters)
# --------------------------------------------------
def jhu_ms_cs_count():
    return run_query("""
        SELECT COUNT(*)
        FROM applicants
        WHERE degree ILIKE '%master%'
          AND program ILIKE '%computer science%'
          AND (
                program ILIKE '%johns hopkins%'
             OR program ILIKE '%jhu%'
          );
    """, fetchone=True)

# --------------------------------------------------
# QUESTION 8 (RAW university field)
# --------------------------------------------------
def phd_cs_acceptances_2026_raw_university():
    return run_query("""
        SELECT COUNT(*)
        FROM applicants
        WHERE term = 'Fall 2026'
          AND status = 'accepted'
          AND degree ILIKE '%phd%'
          AND program ILIKE '%computer science%'
          AND (
                program ILIKE '%georgetown%'
             OR program ILIKE '%mit%'
             OR program ILIKE '%massachusetts institute of technology%'
             OR program ILIKE '%stanford%'
             OR program ILIKE '%carnegie mellon%'
          );
    """, fetchone=True)

# --------------------------------------------------
# QUESTION 9 (LLM-generated university field)
# --------------------------------------------------
def phd_cs_acceptances_2026_llm_university():
    return run_query("""
        SELECT COUNT(*)
        FROM applicants
        WHERE term = 'Fall 2026'
          AND status = 'accepted'
          AND degree ILIKE '%phd%'
          AND llm_generated_program ILIKE '%computer science%'
          AND llm_generated_university IN (
              'Georgetown University',
              'Massachusetts Institute of Technology',
              'Stanford University',
              'Carnegie Mellon University'
          );
    """, fetchone=True)

# --------------------------------------------------
# ADDITIONAL QUESTION 1
# --------------------------------------------------
def avg_gpa_by_citizenship():
    return run_query("""
        SELECT us_or_international, ROUND(AVG(gpa)::numeric, 2)
        FROM applicants
        WHERE gpa IS NOT NULL
        GROUP BY us_or_international;
    """)

# --------------------------------------------------
# ADDITIONAL QUESTION 2
# --------------------------------------------------
def acceptance_rate_by_degree():
    return run_query("""
        SELECT
            degree,
            ROUND(
                (100.0 * SUM(CASE WHEN status = 'accepted' THEN 1 ELSE 0 END)
                / COUNT(*))::numeric, 2
            )
        FROM applicants
        GROUP BY degree;
    """)
