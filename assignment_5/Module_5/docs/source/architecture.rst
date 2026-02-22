Architecture
============

Web Layer (Flask)
-----------------

- Routes live in ``src/M3_material/board/pages.py``.
- ``/analysis`` renders the analysis dashboard.
- ``/pull-data`` and ``/update-analysis`` provide JSON endpoints for the UI.

ETL Layer (Scrape → Clean → Load)
----------------------------------

- Scraping is implemented in ``src/M2_material/scrape.py``.
- Cleaning/normalization is in ``src/M2_material/clean.py`` and
  ``src/db/normalize.py``.
- Data is inserted into PostgreSQL via ``src/db/load_data.py`` and
  ``src/db/import_extra_data.py``.

Database Layer
--------------

- Connection config is centralized in ``src/db/db_config.py``.
- Migrations are managed by ``src/db/migrate.py``.
- Query logic for analysis lives in ``src/M3_material/query_data.py``.
