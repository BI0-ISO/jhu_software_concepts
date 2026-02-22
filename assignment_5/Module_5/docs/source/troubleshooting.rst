Troubleshooting
===============

Database Connection Errors
--------------------------

- Ensure PostgreSQL is running.
- Verify ``DATABASE_URL`` points to the correct host/port/db.

Test Failures Due to Busy State
-------------------------------

- Tests should not use live scrapes or sleeps. Use injected handlers
  and the Flask test client.

Docs Build Errors
-----------------

- Run from ``docs/``: ``make html``
- Ensure ``sphinx`` and ``sphinx-rtd-theme`` are installed.
