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
