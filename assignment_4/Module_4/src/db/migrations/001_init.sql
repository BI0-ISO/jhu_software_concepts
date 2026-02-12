-- Initial schema for Module 3.
-- Aligns with SCHEMA_OVERVIEW.md and adds pull job tracking.

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
    llm_generated_university TEXT
);

-- Ensure columns exist if an older schema was used.
ALTER TABLE applicants ADD COLUMN IF NOT EXISTS comments TEXT;
ALTER TABLE applicants ADD COLUMN IF NOT EXISTS date_added DATE;
ALTER TABLE applicants ADD COLUMN IF NOT EXISTS acceptance_date DATE;
ALTER TABLE applicants ADD COLUMN IF NOT EXISTS url TEXT;
ALTER TABLE applicants ADD COLUMN IF NOT EXISTS us_or_international TEXT;
ALTER TABLE applicants ADD COLUMN IF NOT EXISTS degree TEXT;
ALTER TABLE applicants ALTER COLUMN degree TYPE TEXT USING degree::text;
ALTER TABLE applicants ALTER COLUMN date_added TYPE DATE USING date_added::date;

-- Remove duplicate URLs before enforcing uniqueness.
DELETE FROM applicants a
USING applicants b
WHERE a.url = b.url
  AND a.p_id < b.p_id
  AND a.url IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_applicants_url ON applicants (url);

-- Track pull runs in the database for status/history.
CREATE TABLE IF NOT EXISTS pull_jobs (
    id SERIAL PRIMARY KEY,
    status TEXT,
    started_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    inserted INTEGER DEFAULT 0,
    duplicates INTEGER DEFAULT 0,
    processed INTEGER DEFAULT 0,
    target INTEGER DEFAULT 0,
    last_attempted INTEGER,
    error TEXT
);
