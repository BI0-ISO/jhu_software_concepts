Testing Guide
============

Run the full marked suite:

.. code-block:: bash

   pytest -m "web or buttons or analysis or db or integration"

Markers
-------

- ``web``: Flask route/page rendering tests.
- ``buttons``: Busy-state behavior for pull/update endpoints.
- ``analysis``: Formatting + labels + analysis structure.
- ``db``: Schema, inserts, idempotency.
- ``integration``: End-to-end pull → update → render.

Selectors
---------

Stable selectors used in UI tests:

- ``data-testid="pull-data-btn"``
- ``data-testid="update-analysis-btn"``

Fixtures / Test Doubles
-----------------------

Tests inject behavior via ``app.config``:

- ``PULL_HANDLER`` to fake a pull without scraping.
- ``UPDATE_HANDLER`` to bypass real analysis updates.
- ``PULL_RUNNING_CHECK`` / ``LLM_READY_CHECK`` to control busy and readiness state.
