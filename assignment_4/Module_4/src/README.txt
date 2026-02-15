MODULE 3 README
===============

Overview
--------
This folder contains the full Module 3 web app and data pipeline. The app
renders a dashboard and PDF report that answer the assignment questions.
The pipeline scrapes GradCafe result pages, cleans them, standardizes
program/university names with a local LLM, and inserts the results into a
PostgreSQL database. The dashboard queries that database and caches results
for fast page loads.

Folder Layout
-------------
- run.py
  Entry point for the Flask app. Registers Module 1 and Module 3 routes and
  auto-starts the local LLM server if it is not already running.

- M2_material/
  Scraping and cleaning logic (Module 2 code reused in Module 3).
  - scrape.py: fetches GradCafe HTML by result ID and yields raw pages.
  - clean.py: extracts structured fields from HTML.
  - pull_data.py: end-to-end pull script (scrape -> clean -> LLM -> insert).

- M3_material/
  Module 3 dashboard and reporting.
  - board/pages.py: Flask routes for the Module 3 dashboard and pull controls.
  - query_data.py: SQL queries used to answer the assignment questions.
  - reporting.py: generates a lightweight PDF report from query results.
  - templates/project_module_3.html: HTML dashboard layout.

- db/
  Database utilities and schema.
  - db_config.py: Postgres connection settings.
  - import_extra_data.py: import a large cleaned JSON/JSONL file into the DB.
  - load_data.py: load JSON/JSONL into the DB (smaller batch).
  - normalize.py: field normalization and cleaning helpers.

- llm_hosting/
  Local LLM service used to standardize program/university names.
  - app.py: Flask API with /standardize, /status, /ready endpoints.

- static/
  - css/style.css: styling for all pages.
  - reports/module_3_report.pdf: generated report (created on Update Analysis).


Database Schema (SCHEMA_OVERVIEW)
---------------------------------
The applicants table matches SCHEMA_OVERVIEW.md exactly:
  p_id (integer)
  program (text)
  comments (text)
  date_added (date)
  acceptance_date (date)
  url (text)
  status (text)
  term (text)
  us_or_international (text)
  gpa (float)
  gre (float)
  gre_v (float)
  gre_aw (float)
  degree (text)
  llm_generated_program (text)
  llm_generated_university (text)

The schema is created automatically in pull_data.py and import_extra_data.py
if it does not exist.

Migrations
----------
Schema changes are now managed via db/migrate.py and db/migrations/*.sql.
This ensures a single, explicit source of truth for the applicants table,
indexes, and pull job tracking. The migration also adds a unique index on
the URL field to prevent duplicate insertions.


How Pull Data Works (Scrape -> Clean -> LLM -> Insert)
-----------------------------------------------------
1) Determine the latest ID already in the database.
   pull_data.py queries the DB for the maximum result ID from the stored URLs.

2) Determine the newest GradCafe ID.
   scrape.py fetches https://www.thegradcafe.com/survey/ and reads the highest
   /result/<id> on the page. This caps the scrape range.

3) Scrape new entries only.
   scrape_data(start_id, end_id) iterates IDs, skips placeholder pages
   (31/12/1969), and yields HTML + URL + Added On date.

4) Clean raw HTML into structured fields.
   clean.py extracts program, university, decision info, term/year, GRE/GPA,
   and comments.

5) Standardize program/university via the LLM.
   The local LLM (llm_hosting/app.py) receives a batch of rows and returns
   llm_generated_program and llm_generated_university.

6) Normalize and insert into Postgres.
   pull_data.py converts fields to the schema format (dates, numeric parsing,
   GPA range checks, etc.) and inserts new rows. Duplicates by URL are skipped.

7) Write progress for the UI.
   A JSON progress file is written so the webpage can show ETA and counts.

If the pull takes too long or the network fails repeatedly, the pull ends
gracefully with a status message so the user can retry.


Update Analysis and PDF
-----------------------
- The dashboard uses query_data.py to compute results.
- Results are cached in db/analysis_cache.json for fast loads.
- Clicking "Update Analysis" recomputes results and regenerates the PDF report.


How the Questions Are Answered
------------------------------
The dashboard answers the assignment questions in two cohorts:

1) 2026 cohort:
   - term = "Fall" AND date_added in 2026, OR
   - accepted applicants notified in 2026
     (acceptance_date or date_added in 2026).
   This matches Fall-term entries added in 2026 plus 2026 acceptances.

2) All entries:
   - same queries, but without any term/year filter.

Each question maps directly to an SQL query in M3_material/query_data.py.
The PDF report also records the exact SQL text used for each answer.


LLM Standardization
-------------------
The local LLM standardizes program and university names so that:
- abbreviations are expanded (ex: UBC -> University of British Columbia)
- misspellings are corrected
- program names are normalized for consistent filtering


How to Run
----------
1) Ensure Postgres is running and db/db_config.py is correct.
2) Start the app:
   python run.py

The app auto-starts the LLM server. The dashboard will show LLM status.

Pull Data Workflow
------------------
1) Click "Pull Data" to scrape up to TARGET_NEW_RECORDS new entries.
2) Wait for the ETA to complete (progress updates every few seconds).
3) Click "Update Analysis" to recompute the statistics and regenerate the PDF.

If a pull gets stuck, use "Cancel Pull" to terminate it and retry.

System Health Panel
-------------------
The dashboard includes a health section showing:
- Latest DB ID (highest GradCafe result ID stored)
- Latest Survey ID (most recent ID on GradCafe)
- Analysis cache last-updated timestamp
- Last pull job status and counts (stored in pull_jobs table)


Environment Variables (Optional)
--------------------------------
- TARGET_NEW_RECORDS: max new records per pull (default 100)
- LLM_HOST / LLM_PORT: LLM server address (default 127.0.0.1:8000)
- LLM_HOST_URL: full standardize endpoint if different
- LLM_TIMEOUT: per-request timeout (default 60 seconds)
- LLM_BATCH_SIZE: rows per LLM call (default 8)
- PULL_MAX_SECONDS: max seconds per pull before timeout (default 600)


Importing Extra Data
--------------------
To import a large cleaned JSON/JSONL file:
  python db/import_extra_data.py --path M3_material/data/extra_llm_applicant_data.json --recreate

This rebuilds the applicants table using the cleaned file and invalidates the
analysis cache so the dashboard shows updated results.


Documentation (Sphinx)
----------------------
HTML docs live in Module_4/docs. Build them with:

  cd ../docs
  python -m pip install -r requirements.txt
  python -m pip install -r ../src/requirements.txt
  make html

Open the generated HTML at:
  docs/_build/html/index.html
