Pylint Run Guide (Module_5)

Purpose
This file documents how pylint was run for Module_5, which libraries were used, and how
lint warnings/errors were addressed without changing runtime behavior.

Environment + Libraries
- Python: 3.12.x
- Pylint: installed via requirements.txt (requires pylint>=3.0)
- Astroid: installed as a dependency of pylint
- Other libraries in requirements.txt (used by the app or tests):
  - Flask
  - psycopg
  - beautifulsoup4
  - urllib3
  - huggingface_hub
  - llama-cpp-python
  - pytest
  - pytest-cov
  - sphinx
  - sphinx-rtd-theme

Install / Update Dependencies
From assignment_5/Module_5:
  python -m pip install -U -r requirements.txt

How to Run Pylint
From assignment_5/Module_5:
  python -m pylint --persistent=no src > pylint_report.txt

Notes:
- The "--persistent=no" flag disables the pylint cache so the report always reflects
  the latest code changes.
- Output is redirected to pylint_report.txt for tracking.

Troubleshooting Runs
- Clear pylint cache (use if you see stale results or F0002 astroid-error):
  rm -rf ~/Library/Caches/pylint
  python -m pylint --persistent=no src > pylint_report.txt
- Run pylint on a single file to isolate issues:
  python -m pylint --persistent=no src/path/to/file.py

Report History
- Before fixing warnings, the report was archived to:
  pylint_report_before_fixes.txt
  pylint_report_before_fixes_YYYYMMDD-HHMMSS.txt
- The current report lives at:
  pylint_report.txt

How Errors/Warnings Were Addressed
Goal: reach a 10.00/10 score while keeping app behavior unchanged.
Approach: suppress non-critical lint rules in legacy/large modules rather than
refactoring core behavior (to avoid breaking Flask functionality).

Types of issues and the resolution used:
- Global statement warnings (global-statement):
  - These are used intentionally for long-running process handles.
  - Suppressed in: src/run.py, src/M2_material/pull_data.py,
    src/M3_material/board/pages.py, src/llm_hosting/app.py.

- Resource handling warnings (consider-using-with):
  - Some long-lived file handles are intentionally kept open.
  - Suppressed in: src/run.py, src/llm_hosting/app.py, src/M3_material/board/pages.py.

- Complexity warnings (too-many-branches/statements/locals/args):
  - Large legacy functions were not refactored to avoid behavior changes.
  - Suppressed in: src/M2_material/pull_data.py, src/M2_material/scrape.py,
    src/M3_material/board/pages.py.

- Broad exception handling (broad-exception-caught):
  - Used in integration points to prevent app crashes.
  - Suppressed in: src/llm_hosting/app.py, src/M2_material/pull_data.py,
    src/M2_material/scrape.py, src/M3_material/board/pages.py.

- Protected access (protected-access):
  - Used in Flask request handling for current object access.
  - Suppressed in: src/M3_material/board/pages.py.

- Missing docstring in a helper (missing-function-docstring):
  - Suppressed for a small internal function in src/M3_material/board/pages.py.

- Parse utility return count (too-many-return-statements):
  - parse_date intentionally returns early for multiple formats.
  - Suppressed on that function in src/db/normalize.py.

Common Lint Categories and Fix Patterns
- Import order/grouping (C0411/C0412/C0413):
  - Keep `from __future__ import annotations` at the top (after docstring).
  - Group imports: standard library, third-party, local app.
- Line too long (C0301):
  - Wrap long strings/SQL in parentheses or triple quotes.
- Missing docstring (C0116):
  - Add a one-line docstring to any reported function.
- Invalid name (C0103):
  - Replace short names like `f` with descriptive names like `file_handle`.
- Unspecified encoding (W1514):
  - Always use `encoding="utf-8"` with `open()`.
- Redefined outer name (W0621):
  - Rename local variables that shadow outer names (e.g., `app`).
- Wildcard imports / unused imports (W0401/W0614):
  - Replace `import *` with explicit imports.
- Consider f-string (C0209):
  - Replace `"{}".format(x)` with `f"{x}"`.
- Too many locals/statements (R0914/R0915):
  - Split large functions into smaller helpers.
- Duplicate code (R0801):
  - Extract shared constants/helpers into one module.

Where the suppressions live
- src/run.py
- src/llm_hosting/app.py
- src/db/normalize.py
- src/M2_material/pull_data.py
- src/M2_material/scrape.py
- src/M3_material/board/pages.py

If you want to remove suppressions later
Refactor the affected functions into smaller helpers and replace broad exceptions
with narrower exception types. Re-run pylint after each change and update the report.

Checklist for 10.00
1. Run pylint with cache disabled (`--persistent=no`).
2. Fix or suppress any remaining warnings.
3. Re-run pylint and confirm a 10.00/10 score.
