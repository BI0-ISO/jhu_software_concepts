# Module 5 – Grad Cafe Analytics

This module provides a Flask-based analysis dashboard and a PostgreSQL-backed ETL pipeline for GradCafe data. It includes a full pytest suite and Sphinx documentation.

## Project Structure

- `src/`: application code (Flask app, ETL, DB, queries)
- `tests/`: all pytest tests (marked with `web`, `buttons`, `analysis`, `db`, `integration`)
- `pytest.ini`: pytest configuration and coverage settings
- `docs/`: Sphinx documentation source

## Setup

1. Create and activate a virtual environment:

```bash
cd jhu_software_concepts/assignment_5/Module_5
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

2. Configure the database:

- Preferred: set `DATABASE_URL=postgresql://USER:PASSWORD@HOST:PORT/DBNAME`
- Or set `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` (see `.env.example`).

3. Initialize the schema (optional for tests; required for running the app):

```bash
python src/db/import_extra_data.py --recreate
```

4. Run the Flask app:

```bash
python src/run.py
```

## Fresh Install (pip)

```bash
cd jhu_software_concepts/assignment_5/Module_5
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Fresh Install (uv)

```bash
cd jhu_software_concepts/assignment_5/Module_5
uv venv .venv
source .venv/bin/activate
uv pip sync requirements.txt
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

### Section 8 – Sphinx Documentation (Overview, Architecture, API, Testing)

Requirement summary: Sphinx docs are configured and published via Read the Docs, and include overview/setup, architecture, API reference, and testing guidance.

Evidence:

- Sphinx configuration is in `assignment_4/Module_4/docs/source/conf.py`.
- Documentation pages:
  - Overview & setup: `assignment_4/Module_4/docs/source/overview.rst`
  - Architecture: `assignment_4/Module_4/docs/source/architecture.rst`
  - API reference (autodoc): `assignment_4/Module_4/docs/source/api.rst`
  - Testing guide: `assignment_4/Module_4/docs/source/testing.rst`
- Read the Docs integration uses `.readthedocs.yaml` at repo root:
  - `jhu_software_concepts/.readthedocs.yaml` points to `assignment_4/Module_4/docs/source/conf.py`.
- Required folder structure is present:
  - `assignment_4/Module_4/src`, `assignment_4/Module_4/tests`, `assignment_4/Module_4/pytest.ini`,
    `assignment_4/Module_4/requirements.txt`, `assignment_4/Module_4/README.md`,
    `assignment_4/Module_4/docs`.

## Full Checklist (Required Items)

This section confirms each required item and where it is implemented.

- **GET `/analysis` renders required components**: Verified in `assignment_4/Module_4/tests/test_flask_page.py` (status 200, “Analysis”, “Answer:”, and both buttons).
- **POST `/pull-data` returns 200/202 and triggers loader when not busy**: Verified in `assignment_4/Module_4/tests/test_buttons.py` using injected `PULL_HANDLER`.
- **Busy gating for `/pull-data` and `/update-analysis`**: Verified in `assignment_4/Module_4/tests/test_buttons.py` (returns 409 and does not run handlers).
- **Analysis formatting (two decimals + “Answer:”)**: Verified in `assignment_4/Module_4/tests/test_analysis_format.py`.
- **DB writes after `/pull-data`**: Verified in `assignment_4/Module_4/tests/test_db_insert.py` (non‑null required fields).
- **Idempotency / no duplicate rows**: Verified in `assignment_4/Module_4/tests/test_db_insert.py`.
- **Query results contain required keys**: Verified in `assignment_4/Module_4/tests/test_analysis_format.py`.
- **End‑to‑end flow (pull → update → render)**: Verified in `assignment_4/Module_4/tests/test_integration_end_to_end.py`.
- **All tests marked (`web`, `buttons`, `analysis`, `db`, `integration`)**: Markers defined in `assignment_4/Module_4/pytest.ini`, and all tests use `pytestmark` or `@pytest.mark.*`.
- **Marker command runs full suite**: `pytest -m "web or buttons or analysis or db or integration"` (documented in README and validated by coverage enforcement in `pytest.ini`).
- **Flask `create_app(...)` factory**: Implemented in `assignment_4/Module_4/src/run.py`.
- **Stable UI selectors**: `data-testid="pull-data-btn"` and `data-testid="update-analysis-btn"` in `assignment_4/Module_4/src/M3_material/templates/project_module_3.html`.
- **`DATABASE_URL` support**: Implemented in `assignment_4/Module_4/src/db/db_config.py`.
- **Sphinx docs (overview, architecture, API, testing) + published HTML**: Implemented in `assignment_4/Module_4/docs/source/*.rst` and published at the Read the Docs URL listed above.

## Should-Have Checklist (Recommended Items)

This section maps each “SHOULD” item to where it is implemented.

- **Dependency injection for tests**: Implemented via `app.config` overrides (e.g., `PULL_HANDLER`, `UPDATE_HANDLER`, `PULL_RUNNING_CHECK`, `LLM_READY_CHECK`) in `assignment_4/Module_4/tests/test_buttons.py` and `assignment_4/Module_4/tests/test_integration_end_to_end.py`.
- **BeautifulSoup + regex for HTML assertions**: Used in `assignment_4/Module_4/tests/test_flask_page.py` and `assignment_4/Module_4/tests/test_analysis_format.py` (regex enforces two-decimal percentages).
- **Negative/error-path tests**: Covered throughout the suite (e.g., error branches in `assignment_4/Module_4/tests/test_pages_module.py`, `assignment_4/Module_4/tests/test_pull_data_module.py`, `assignment_4/Module_4/tests/test_scrape_module.py`).
- **CI workflow with Postgres**: Provided in `jhu_software_concepts/.github/workflows/tests.yml` (starts Postgres and runs pytest).
- **Fast, deterministic tests**: Network and scraper calls are mocked; tests use Flask’s test client and controlled fixtures.
- **Operational notes page**: Implemented in `assignment_4/Module_4/docs/source/operational_notes.rst`.
- **Troubleshooting page**: Implemented in `assignment_4/Module_4/docs/source/troubleshooting.rst`.

## Shall-Not Checklist (Prohibited Items)

This section confirms the suite avoids prohibited practices.

- **No tests depend on live internet or long scrapes**: Scraper and network calls are mocked (e.g., `assignment_4/Module_4/tests/test_scrape_module.py`, `test_pages_module.py`).
- **No arbitrary sleep for busy-state checks**: Busy state is injected via `app.config` (`PULL_RUNNING_CHECK`, `LLM_READY_CHECK`) in tests like `assignment_4/Module_4/tests/test_buttons.py`.
- **No unmarked tests**: All tests use `pytestmark` or `@pytest.mark.*` and markers are defined in `assignment_4/Module_4/pytest.ini`.
- **No variable precision percentages**: Enforced by `assignment_4/Module_4/tests/test_analysis_format.py`.
- **No schema-breaking changes**: Tests exercise the existing Module‑3 schema via `db/migrate.py` and insert/select operations (`assignment_4/Module_4/tests/test_db_insert.py`, `test_db_loaders.py`).
- **No hard-coded secrets**: No secrets in code/tests; database access uses `DATABASE_URL` (`assignment_4/Module_4/src/db/db_config.py`).
- **No manual UI interaction**: All UI checks use Flask’s test client (e.g., `assignment_4/Module_4/tests/test_flask_page.py`).

## Deliverables Checklist

- **SSH URL to GitHub repository**: `git@github.com:BI0-ISO/jhu_software_concepts.git`  
- **README under Module_4**: Present at `assignment_4/Module_4/README.md`.
- **requirements.txt under Module_4**: Present at `assignment_4/Module_4/requirements.txt`.
- **Sphinx generated HTML**: Present at `assignment_4/Module_4/docs/build/html/index.html`.
- **Proof of coverage**: Present at `assignment_4/Module_4/coverage_summary.txt`.
- **GitHub Actions proof**:
  - Workflow file present at `assignment_4/Module_4/.github/workflows/tests.yml`.
  - `actions_success.png` **missing** — add after a green run.
- **Read the Docs link**: Present above in this README.
- **All listed test files under Module_4**: Present in `assignment_4/Module_4/tests/`.

## Documentation

Sphinx docs live in `docs/` and include setup, architecture, API references, and testing guidance.

Build docs locally:

```bash
cd docs
make html
```

Read the Docs URL: https://jhu-software-concepts-sphinxspring2026.readthedocs.io/en/latest/

## CI

A minimal GitHub Actions workflow is provided at `.github/workflows/tests.yml`. After your workflow succeeds, save a screenshot as `actions_success.png`.
