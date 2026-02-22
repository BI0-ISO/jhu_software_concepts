"""
Tests for the local LLM hosting Flask app.

All model calls are mocked to keep tests fast and deterministic.
"""

import json
from pathlib import Path

import pytest

from llm_hosting import app as llm_app

pytestmark = pytest.mark.analysis


def test_best_match_and_post_normalize_helpers(monkeypatch):
    # Provide small canonical lists for matching.
    monkeypatch.setattr(llm_app, "CANON_PROGS", ["Computer Science"])
    monkeypatch.setattr(llm_app, "CANON_UNIS", ["Johns Hopkins University"])

    assert llm_app._best_match("Computer Science", llm_app.CANON_PROGS, cutoff=0.5) == "Computer Science"
    assert llm_app._post_normalize_program("computer science") == "Computer Science"
    assert llm_app._post_normalize_university("JHU") == "Johns Hopkins University"
    # Empty candidates or names should return None.
    assert llm_app._best_match("", []) is None
    # Empty university should fall back to Unknown.
    assert llm_app._post_normalize_university("") == "Unknown"


def test_read_lines_missing_file():
    # Missing canonical files should simply return an empty list.
    assert llm_app._read_lines("definitely_missing.txt") == []


def test_read_lines_success(tmp_path):
    # _read_lines should strip blanks and whitespace.
    path = tmp_path / "canon.txt"
    path.write_text("A\n\n B \n")
    assert llm_app._read_lines(str(path)) == ["A", "B"]


def test_normalize_input_shapes():
    # _normalize_input should accept list or {"rows": [...]} payloads.
    assert llm_app._normalize_input([{ "program": "CS" }]) == [{"program": "CS"}]
    assert llm_app._normalize_input({"rows": [{"program": "CS"}]}) == [{"program": "CS"}]
    assert llm_app._normalize_input({"bad": 1}) == []


def test_call_llm_success(monkeypatch):
    # Fake LLM that returns a JSON payload the parser can read.
    class DummyLLM:
        def create_chat_completion(self, **kwargs):
            return {
                "choices": [
                    {"message": {"content": json.dumps({
                        "standardized_program": "Computer Science",
                        "standardized_university": "Johns Hopkins University",
                    })}}
                ]
            }

    monkeypatch.setattr(llm_app, "_load_llm", lambda: DummyLLM())
    result = llm_app._call_llm("Computer Science", "Johns Hopkins University")
    assert result["standardized_program"] == "Computer Science"
    assert result["standardized_university"] == "Johns Hopkins University"


def test_call_llm_fallback_on_error(monkeypatch):
    # Force an exception so the fallback path is used.
    class DummyLLM:
        def create_chat_completion(self, **kwargs):
            raise RuntimeError("fail")

    monkeypatch.setattr(llm_app, "_load_llm", lambda: DummyLLM())
    result = llm_app._call_llm("Math", "Test University")
    assert result["standardized_program"]
    assert result["standardized_university"]


def test_call_llm_bad_json_falls_back(monkeypatch):
    # Return malformed JSON to hit the exception branch.
    class DummyLLM:
        def create_chat_completion(self, **kwargs):
            return {"choices": [{"message": {"content": "not-json"}}]}

    monkeypatch.setattr(llm_app, "_load_llm", lambda: DummyLLM())
    result = llm_app._call_llm("Physics", "Unknown U")
    assert result["standardized_program"]
    assert result["standardized_university"]


def test_call_llm_final_fallbacks(monkeypatch):
    # Force post-normalize to return empty strings so the final fallback runs.
    class DummyLLM:
        def create_chat_completion(self, **kwargs):
            return {
                "choices": [
                    {"message": {"content": json.dumps({
                        "standardized_program": "",
                        "standardized_university": "",
                    })}}
                ]
            }

    monkeypatch.setattr(llm_app, "_load_llm", lambda: DummyLLM())
    monkeypatch.setattr(llm_app, "_post_normalize_program", lambda *_: "")
    monkeypatch.setattr(llm_app, "_post_normalize_university", lambda *_: "")

    result = llm_app._call_llm("Chemistry", "Test U")
    assert result["standardized_program"] == "Chemistry"
    assert result["standardized_university"] == "Test U"


def test_llm_flask_endpoints(monkeypatch):
    # Mock _load_llm to avoid loading a real model.
    monkeypatch.setattr(llm_app, "_load_llm", lambda: object())

    client = llm_app.app.test_client()

    # Health endpoint should always return ok.
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.get_json()["ok"] is True

    # Status depends on whether _LLM is loaded.
    llm_app._LLM = None
    resp = client.get("/status")
    assert resp.get_json()["model_loaded"] is False

    llm_app._LLM = object()
    resp = client.get("/status")
    assert resp.get_json()["model_loaded"] is True

    # Ready endpoint should call _load_llm and report loaded.
    resp = client.get("/ready")
    assert resp.get_json()["model_loaded"] is True

    # Standardize endpoint should return rows with LLM fields.
    monkeypatch.setattr(llm_app, "_call_llm", lambda program_text, original_uni=None: {
        "standardized_program": program_text or "",
        "standardized_university": original_uni or "",
    })
    resp = client.post("/standardize", json={"rows": [{"program": "CS", "university": "JHU"}]})
    assert resp.status_code == 200
    assert resp.get_json()["rows"][0]["llm_generated_program"] == "CS"
    # Reset global state to avoid leaking between tests.
    llm_app._LLM = None


def test_load_llm_uses_hf_download(monkeypatch, tmp_path):
    # Patch hf_hub_download and Llama to avoid real model downloads.
    dummy_model = tmp_path / "model.gguf"
    dummy_model.write_text("fake")

    monkeypatch.setattr(llm_app, "hf_hub_download", lambda **kwargs: str(dummy_model))

    class DummyLlama:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    monkeypatch.setattr(llm_app, "Llama", DummyLlama)

    llm_app._LLM = None
    model = llm_app._load_llm()
    assert isinstance(model, DummyLlama)


def test_load_llm_returns_cached(monkeypatch):
    # If _LLM is already set, _load_llm should return it without downloading.
    cached = object()
    llm_app._LLM = cached
    monkeypatch.setattr(llm_app, "hf_hub_download", lambda **kwargs: (_ for _ in ()).throw(RuntimeError("should not download")))
    assert llm_app._load_llm() is cached
    llm_app._LLM = None


def test_cli_process_file_stdout_and_file(monkeypatch, tmp_path, capsys):
    # Prepare 1000 rows so the progress log (i % 1000) branch executes.
    rows = [{"program": "CS", "university": "JHU"} for _ in range(1000)]
    in_path = tmp_path / "input.json"
    in_path.write_text(json.dumps(rows))

    monkeypatch.setattr(
        llm_app,
        "_call_llm",
        lambda program_text, original_uni=None: {
            "standardized_program": program_text or "",
            "standardized_university": original_uni or "",
        },
    )

    out_path = tmp_path / "out.jsonl"
    llm_app._cli_process_file(str(in_path), str(out_path), append=False, to_stdout=False)

    # Progress should have been logged to stderr at 1000 rows.
    captured = capsys.readouterr()
    assert "Processed 1000 rows" in captured.err
    assert out_path.exists()

    # Also verify stdout mode writes JSONL to stdout (use a tiny input).
    small_path = tmp_path / "small.json"
    small_path.write_text(json.dumps([{"program": "Math", "university": "U"}]))
    llm_app._cli_process_file(str(small_path), None, append=False, to_stdout=True)
    out = capsys.readouterr().out
    assert "\"llm_generated_program\"" in out


def test_llm_app_main_serve_and_cli(monkeypatch, tmp_path):
    # Execute the module as __main__ for both serve and CLI branches.
    import runpy
    import types
    import sys

    # Fake out external dependencies to avoid downloads.
    fake_hf = types.ModuleType("huggingface_hub")
    fake_hf.hf_hub_download = lambda **kwargs: str(tmp_path / "model.gguf")
    fake_llama = types.ModuleType("llama_cpp")

    class DummyLlama:
        def __init__(self, **kwargs):
            pass

        def create_chat_completion(self, **kwargs):
            return {
                "choices": [
                    {"message": {"content": json.dumps({
                        "standardized_program": "CS",
                        "standardized_university": "JHU",
                    })}}
                ]
            }

    fake_llama.Llama = DummyLlama

    monkeypatch.setitem(sys.modules, "huggingface_hub", fake_hf)
    monkeypatch.setitem(sys.modules, "llama_cpp", fake_llama)

    # Patch Flask.run to avoid starting a real server.
    import flask
    monkeypatch.setattr(flask.Flask, "run", lambda *a, **k: None)

    # Serve branch.
    monkeypatch.setattr(sys, "argv", ["app.py", "--serve"])
    root = Path(__file__).resolve().parents[1]
    runpy.run_path(str(root / "src" / "llm_hosting" / "app.py"), run_name="__main__")

    # CLI branch with an input file.
    input_path = tmp_path / "input.json"
    input_path.write_text(json.dumps([{"program": "CS", "university": "JHU"}]))
    monkeypatch.setattr(sys, "argv", ["app.py", "--stdout", str(input_path)])
    runpy.run_path(str(root / "src" / "llm_hosting" / "app.py"), run_name="__main__")
