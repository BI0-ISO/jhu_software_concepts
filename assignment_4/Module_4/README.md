# Module 4 – Grad Cafe Analytics

This module provides a Flask-based analysis dashboard and a PostgreSQL-backed ETL pipeline for GradCafe data. It includes a full pytest suite and Sphinx documentation.

## Project Structure

- `src/`: application code (Flask app, ETL, DB, queries)
- `tests/`: all pytest tests (marked with `web`, `buttons`, `analysis`, `db`, `integration`)
- `pytest.ini`: pytest configuration and coverage settings
- `docs/`: Sphinx documentation source

## Setup

1. Create and activate a virtual environment:

```bash
cd jhu_software_concepts/assignment_4/Module_4
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

2. Configure the database:

- Preferred: set `DATABASE_URL=postgresql://USER:PASSWORD@HOST:PORT/DBNAME`
- Otherwise defaults in `src/db/db_config.py` are used.

3. Initialize the schema (optional for tests; required for running the app):

```bash
python src/db/import_extra_data.py --recreate
```

4. Run the Flask app:

```bash
python src/run.py
```

## Tests

Run the full marked suite:

```bash
pytest -m "web or buttons or analysis or db or integration"
```

Coverage is enforced at 100% by `pytest.ini`. After running tests, copy the terminal coverage summary into `coverage_summary.txt`.

## Assignment Evidence

### Section 1 – Project Structure + Flask Page Rendering Tests

Requirement summary: Module 4 is a copy of Module 3 with code moved into `src/` and tests in `tests/`, plus Flask page rendering tests for `/analysis`.

Evidence:

- Project structure matches the required layout: `src/` and `tests/` exist at `assignment_4/Module_4/src` and `assignment_4/Module_4/tests`.
- Flask app factory and routes are verified in `assignment_4/Module_4/tests/test_flask_page.py` (checks required routes and that a testable app is created).
- `/analysis` page load returns 200, and HTML contains “Pull Data”, “Update Analysis”, “Analysis”, and at least one “Answer:” label in `assignment_4/Module_4/tests/test_flask_page.py`.

### Section 2 – Buttons & Busy-State Behavior

Requirement summary: JSON endpoints for `/pull-data` and `/update-analysis` must return 200 when not busy, trigger the handler, and return 409 when busy.

Evidence:

- `assignment_4/Module_4/tests/test_buttons.py` covers:
  - `/pull-data` returns 200 and calls the injected handler (`PULL_HANDLER`) when not busy.
  - `/pull-data` returns 409 with `{"busy": true}` when busy.
  - `/update-analysis` returns 200 and calls the injected handler (`UPDATE_HANDLER`) when not busy.
  - `/update-analysis` returns 409 with `{"busy": true}` when busy and does **not** perform updates.

### Section 3 – Analysis Formatting

Requirement summary: analysis output must include “Answer:” labels and percentages formatted to two decimals.

Evidence:

- `assignment_4/Module_4/tests/test_analysis_format.py`:
  - Asserts page text includes “Answer:”.
  - Extracts all percentage strings and enforces two-decimal formatting (`NN.NN%`).

### Section 4 – Database Writes + Query Keys

Requirement summary: inserting rows via `/pull-data` writes required fields, duplicate pulls are idempotent, and query helpers return expected keys.

Evidence:

- `assignment_4/Module_4/tests/test_db_insert.py`:
  - Inserts records via `/pull-data` and verifies required DB fields are non-null.
  - Ensures duplicate pulls do not create duplicate rows.
- `assignment_4/Module_4/tests/test_analysis_format.py`:
  - Validates the analysis results dictionary contains all required keys used by the template.

### Section 5 – Integration Test (End-to-End)

Requirement summary: pull → update → render flow works, uses injected fakes, and maintains idempotency across pulls.

Evidence:

- `assignment_4/Module_4/tests/test_integration_end_to_end.py`:
  - Injects a fake pull handler to insert multiple records.
  - `POST /pull-data` succeeds and records are inserted.
  - `POST /update-analysis` succeeds when not busy.
  - `GET /analysis` renders updated analysis values.
  - Duplicate pulls are covered by idempotency tests in `tests/test_db_insert.py`.

### Section 6 – Pytest Markers (pytest.ini)

Requirement summary: all tests are marked and markers are listed in `pytest.ini`.

Evidence:

- `assignment_4/Module_4/pytest.ini` defines:
  - `web`, `buttons`, `analysis`, `db`, `integration`.
- All tests use `pytestmark` or explicit `@pytest.mark.*` decorators to satisfy the marker policy.

### Section 7 – Marker Policy + Coverage Enforcement

Requirement summary: running `pytest -m "web or buttons or analysis or db or integration"` executes the entire suite, and pytest-cov enforces 100% coverage.

Evidence:

- Marker policy is satisfied by marking every test (see Section 6).
- The full suite is executed with:
  - `pytest -m "web or buttons or analysis or db or integration"`
- Coverage is enforced in `assignment_4/Module_4/pytest.ini`:
  - `--cov=src --cov-report=term-missing --cov-fail-under=100`

## Documentation

Sphinx docs live in `docs/` and include setup, architecture, API references, and testing guidance.

Build docs locally:

```bash
cd docs
make html
```

Read the Docs URL: replace with your published link.

## CI

A minimal GitHub Actions workflow is provided at `.github/workflows/tests.yml`. After your workflow succeeds, save a screenshot as `actions_success.png`.
