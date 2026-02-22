Overview & Setup
================

This project provides a Flask-based analysis dashboard and an ETL pipeline
that ingests GradCafe data into PostgreSQL, then computes summary analytics
for the web UI.

Quick Start
-----------

1. Create and activate a virtual environment:

.. code-block:: bash

   cd jhu_software_concepts/assignment_4/Module_4
   python3 -m venv .venv
   source .venv/bin/activate
   python -m pip install -r requirements.txt

2. Set required environment variables:

.. code-block:: bash

   export DATABASE_URL=postgresql://USER:PASSWORD@HOST:PORT/DBNAME

3. Initialize the database schema (optional for tests, required for app):

.. code-block:: bash

   python src/db/import_extra_data.py --recreate

4. Run the Flask app:

.. code-block:: bash

   python src/run.py

Environment Variables
---------------------

- ``DATABASE_URL``: PostgreSQL connection string used by loaders and queries.
- ``LLM_HOST`` / ``LLM_PORT``: LLM service connection parameters.
- ``LLM_HOST_URL``: full URL for the LLM standardization endpoint.
- ``TARGET_NEW_RECORDS``: pull target for ETL job.
- ``PULL_MAX_SECONDS``: max runtime for a pull job.
