"""
End-to-end test for the JSON pull/update flow and HTML rendering.
"""

import pytest
from bs4 import BeautifulSoup


@pytest.mark.integration
def test_pull_update_render_flow(app, client, sample_record, insert_records):
    # End-to-end flow: pull -> update-analysis -> render page.
    # We inject a fake pull handler so the test is fast and deterministic.
    records = [
        sample_record(url="https://www.thegradcafe.com/result/999100", us_or_international="International"),
        sample_record(
            url="https://www.thegradcafe.com/result/999101",
            us_or_international="American",
            status="rejected",
            acceptance_date=None,
        ),
    ]

    def handler():
        # Mimic a pull by inserting records directly.
        insert_records(records)
        return {"inserted": len(records)}

    app.config["PULL_HANDLER"] = handler

    # Trigger the pull via JSON endpoint.
    pull_resp = client.post("/pull-data")
    assert pull_resp.status_code in (200, 202)
    assert pull_resp.get_json()["ok"] is True

    # Recompute analysis via JSON endpoint.
    update_resp = client.post("/update-analysis")
    assert update_resp.status_code == 200
    assert update_resp.get_json() == {"ok": True}

    # Render the analysis page and verify the cohort count updated.
    # This ensures the HTML template is using the updated analysis cache.
    page = client.get("/analysis")
    assert page.status_code == 200
    soup = BeautifulSoup(page.data.decode("utf-8"), "html.parser")

    stat_cards = soup.select(".stat-card")
    target = None
    for card in stat_cards:
        label = card.select_one(".stat-label")
        if label and "2026 cohort entries" in label.get_text():
            target = card
            break
    assert target is not None

    value_text = target.select_one(".stat-value").get_text(strip=True)
    value_text = value_text.replace("Answer:", "").strip()
    assert value_text == "2"
