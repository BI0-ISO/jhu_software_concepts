"""
Unit tests for the scraper helpers.

These avoid live network calls by mocking the HTTP client.
"""

import pytest

from M2_material import scrape

pytestmark = pytest.mark.analysis


class FakeResponse:
    def __init__(self, status, data):
        self.status = status
        self.data = data.encode("utf-8")


class FakeHTTP:
    def __init__(self, responses):
        # Map URL -> FakeResponse
        self.responses = responses

    def request(self, method, url, timeout=None):
        resp = self.responses.get(url)
        if resp is None:
            # Default to 404 if we did not define a response.
            return FakeResponse(404, "")
        return resp


def test_fetch_survey_added_map_and_latest_id(monkeypatch):
    # Build a fake survey page containing an Added On column and one result link.
    html = """
    <table>
      <tr><th>Result</th><th>Added On</th></tr>
      <tr><td><a href="/result/123456">Result</a></td><td>Jan 1, 2026</td></tr>
    </table>
    """
    fake_http = FakeHTTP({"https://www.thegradcafe.com/survey/": FakeResponse(200, html)})
    monkeypatch.setattr(scrape, "http", fake_http)

    mapping = scrape._fetch_survey_added_map()
    assert mapping == {123456: "Jan 1, 2026"}

    latest_id = scrape.get_latest_survey_id()
    assert latest_id == 123456


def test_fetch_survey_added_map_handles_non_200(monkeypatch):
    # Non-200 responses should yield an empty mapping.
    fake_http = FakeHTTP({"https://www.thegradcafe.com/survey/": FakeResponse(500, "oops")})
    monkeypatch.setattr(scrape, "http", fake_http)
    assert scrape._fetch_survey_added_map() == {}


def test_fetch_survey_added_map_missing_added_on(monkeypatch):
    # If the "Added On" column isn't present, return an empty mapping.
    html = "<table><tr><th>Result</th><th>Status</th></tr></table>"
    fake_http = FakeHTTP({"https://www.thegradcafe.com/survey/": FakeResponse(200, html)})
    monkeypatch.setattr(scrape, "http", fake_http)
    assert scrape._fetch_survey_added_map() == {}


def test_fetch_survey_added_map_missing_link_or_bad_match(monkeypatch):
    # Rows without links or with non-matching links should be skipped.
    html = """
    <table>
      <tr><th>Result</th><th>Added On</th></tr>
      <tr><td>No link here</td><td>Jan 1, 2026</td></tr>
      <tr><td><a href="/result/notanumber">Bad</a></td><td>Jan 2, 2026</td></tr>
    </table>
    """
    fake_http = FakeHTTP({"https://www.thegradcafe.com/survey/": FakeResponse(200, html)})
    monkeypatch.setattr(scrape, "http", fake_http)
    assert scrape._fetch_survey_added_map() == {}


def test_fetch_survey_added_map_re_search_none(monkeypatch):
    # Force re.search to return None to hit the "if not match: continue" line.
    html = """
    <table>
      <tr><th>Result</th><th>Added On</th></tr>
      <tr><td><a href="/result/123456">Result</a></td><td>Jan 1, 2026</td></tr>
    </table>
    """
    fake_http = FakeHTTP({"https://www.thegradcafe.com/survey/": FakeResponse(200, html)})
    monkeypatch.setattr(scrape, "http", fake_http)
    monkeypatch.setattr(scrape.re, "search", lambda *a, **k: None)
    assert scrape._fetch_survey_added_map() == {}


def test_fetch_survey_added_map_handles_exception(monkeypatch):
    # Exceptions during fetch should result in an empty mapping.
    class ErrorHTTP:
        def request(self, *args, **kwargs):
            raise Exception("boom")

    monkeypatch.setattr(scrape, "http", ErrorHTTP())
    assert scrape._fetch_survey_added_map() == {}


def test_get_latest_survey_id_handles_non_200_and_error(monkeypatch):
    # Non-200 should return None.
    fake_http = FakeHTTP({"https://www.thegradcafe.com/survey/": FakeResponse(500, "oops")})
    monkeypatch.setattr(scrape, "http", fake_http)
    assert scrape.get_latest_survey_id() is None

    # Exceptions should also return None.
    class ErrorHTTP:
        def request(self, *args, **kwargs):
            raise Exception("boom")

    monkeypatch.setattr(scrape, "http", ErrorHTTP())
    assert scrape.get_latest_survey_id() is None


def test_scrape_data_skips_placeholders(monkeypatch):
    # HTML containing 31/12/1969 should be treated as a placeholder and skipped.
    html = "<div>on 31/12/1969</div>"
    fake_http = FakeHTTP({"https://www.thegradcafe.com/result/1": FakeResponse(200, html)})
    monkeypatch.setattr(scrape, "http", fake_http)
    monkeypatch.setattr(scrape, "_fetch_survey_added_map", lambda: {})

    results = list(
        scrape.scrape_data(
            start_entry=1,
            end_entry=2,
            stop_on_placeholder_streak=True,
            placeholder_limit=1,
        )
    )
    assert results == []
    assert scrape.get_last_stop_reason() == "placeholder_streak"


def test_scrape_data_timeout(monkeypatch):
    # Use max_seconds < 0 to trigger immediate timeout.
    fake_http = FakeHTTP({})
    monkeypatch.setattr(scrape, "http", fake_http)
    monkeypatch.setattr(scrape, "_fetch_survey_added_map", lambda: {})

    results = list(scrape.scrape_data(start_entry=1, end_entry=2, max_seconds=-1))
    assert results == []
    assert scrape.get_last_stop_reason() == "timeout"


def test_scrape_data_error_streak(monkeypatch):
    # Force request to raise to hit the error streak branch.
    class ErrorHTTP:
        def request(self, *args, **kwargs):
            raise Exception("boom")

    monkeypatch.setattr(scrape, "http", ErrorHTTP())
    monkeypatch.setattr(scrape, "_fetch_survey_added_map", lambda: {})

    results = list(scrape.scrape_data(start_entry=1, end_entry=2, max_failures=1))
    assert results == []
    assert scrape.get_last_stop_reason() == "error_streak"


def test_scrape_data_non_200_error_streak(monkeypatch):
    # Non-200 responses should increment failure streak and stop at max_failures.
    fake_http = FakeHTTP({"https://www.thegradcafe.com/result/1": FakeResponse(500, "oops")})
    monkeypatch.setattr(scrape, "http", fake_http)
    monkeypatch.setattr(scrape, "_fetch_survey_added_map", lambda: {})

    results = list(scrape.scrape_data(start_entry=1, end_entry=2, max_failures=1))
    assert results == []
    assert scrape.get_last_stop_reason() == "error_streak"


def test_scrape_data_non_200_then_success(monkeypatch):
    # Non-200 should continue when max_failures not reached, then succeed.
    fake_http = FakeHTTP(
        {
            "https://www.thegradcafe.com/result/1": FakeResponse(500, "oops"),
            "https://www.thegradcafe.com/result/2": FakeResponse(200, "<div>ok</div>"),
        }
    )
    monkeypatch.setattr(scrape, "http", fake_http)
    monkeypatch.setattr(scrape, "_fetch_survey_added_map", lambda: {})

    results = list(scrape.scrape_data(start_entry=1, end_entry=3, max_failures=3))
    assert len(results) == 1


def test_scrape_data_placeholder_continue_then_yield(monkeypatch):
    # A placeholder below the limit should continue to the next entry.
    placeholder_html = "<div>on 31/12/1969</div>"
    good_html = "<div>Decision Accepted</div>"
    fake_http = FakeHTTP(
        {
            "https://www.thegradcafe.com/result/1": FakeResponse(200, placeholder_html),
            "https://www.thegradcafe.com/result/2": FakeResponse(200, good_html),
        }
    )
    monkeypatch.setattr(scrape, "http", fake_http)
    monkeypatch.setattr(scrape, "_fetch_survey_added_map", lambda: {2: "Jan 2, 2026"})

    results = list(scrape.scrape_data(start_entry=1, end_entry=3, placeholder_limit=2))
    assert len(results) == 1
    assert results[0]["url"].endswith("/2")


def test_scrape_data_exception_path_sleeps(monkeypatch):
    # Exceptions should trigger sleep and continue until max_failures is hit.
    class ErrorHTTP:
        def request(self, *args, **kwargs):
            raise Exception("boom")

    sleep_calls = {"count": 0}

    monkeypatch.setattr(scrape, "http", ErrorHTTP())
    monkeypatch.setattr(scrape, "_fetch_survey_added_map", lambda: {})
    monkeypatch.setattr(scrape.time, "sleep", lambda *_: sleep_calls.update(count=sleep_calls["count"] + 1))

    results = list(scrape.scrape_data(start_entry=1, end_entry=2, max_failures=2))
    assert results == []
    assert sleep_calls["count"] == 1


def test_scrape_data_yields_valid_pages(monkeypatch):
    # Provide two valid HTML pages; the generator should yield both.
    html = "<div>Decision Accepted on Jan 1</div>"
    fake_http = FakeHTTP(
        {
            "https://www.thegradcafe.com/result/1": FakeResponse(200, html),
            "https://www.thegradcafe.com/result/2": FakeResponse(200, html),
        }
    )
    monkeypatch.setattr(scrape, "http", fake_http)
    monkeypatch.setattr(scrape, "_fetch_survey_added_map", lambda: {1: "Jan 1, 2026", 2: "Jan 2, 2026"})

    results = list(scrape.scrape_data(start_entry=1, end_entry=3, stop_on_placeholder_streak=False))
    assert len(results) == 2
    assert results[0]["url"].endswith("/1")
    assert results[0]["date_added"] == "Jan 1, 2026"
    # Access the last attempted ID to cover the getter.
    assert scrape.get_last_attempted_id() == 2
