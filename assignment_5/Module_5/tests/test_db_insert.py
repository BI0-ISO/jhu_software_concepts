"""
Database integration tests.

These tests exercise real INSERTs into PostgreSQL using the same schema
the application relies on.
"""

import pytest
import psycopg

from db.db_config import get_db_config


@pytest.mark.db
def test_pull_data_inserts_rows(app, client, sample_record, insert_records):
    # Simulate a pull that inserts a single normalized record.
    # The PULL_HANDLER hook lets tests insert data without running the scraper.
    records = [sample_record()]

    def handler():
        # Insert via the same helper used in other tests so constraints apply.
        insert_records(records)
        return {"inserted": len(records)}

    app.config["PULL_HANDLER"] = handler

    # The endpoint should respond OK and indicate success.
    resp = client.post("/pull-data")
    assert resp.status_code in (200, 202)
    assert resp.get_json()["ok"] is True

    # Verify required fields are populated in the database.
    # We check a subset of columns to keep the test focused.
    with psycopg.connect(**get_db_config(), autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT program, url, status, term, date_added, degree FROM applicants")
            row = cur.fetchone()
            assert row is not None
            assert all(value is not None for value in row)


@pytest.mark.db
def test_pull_data_idempotent(app, client, sample_record, insert_records):
    # Insert the same URL twice and assert only one row exists.
    records = [sample_record(url="https://www.thegradcafe.com/result/999002")]

    def handler():
        # The insert helper uses ON CONFLICT DO NOTHING.
        insert_records(records)
        return {"inserted": len(records)}

    app.config["PULL_HANDLER"] = handler

    # Call the endpoint twice to simulate duplicate pulls.
    resp1 = client.post("/pull-data")
    resp2 = client.post("/pull-data")
    assert resp1.status_code in (200, 202)
    assert resp2.status_code in (200, 202)

    with psycopg.connect(**get_db_config(), autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM applicants")
            count = cur.fetchone()[0]
            assert count == 1
