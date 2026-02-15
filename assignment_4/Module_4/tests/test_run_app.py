"""
Unit tests for src/run.py helpers.

These tests avoid starting real servers by monkeypatching network/process calls.
"""

import types
from pathlib import Path

import pytest

import run

pytestmark = pytest.mark.web


def test_is_port_open_true(monkeypatch):
    # Provide a dummy connection object that supports context manager use.
    class DummyConn:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(run.socket, "create_connection", lambda *args, **kwargs: DummyConn())
    assert run._is_port_open("127.0.0.1", 8000) is True


def test_is_port_open_false(monkeypatch):
    # Force socket.create_connection to raise to simulate a closed port.
    def _raise(*args, **kwargs):
        raise OSError("no connection")

    monkeypatch.setattr(run.socket, "create_connection", _raise)
    assert run._is_port_open("127.0.0.1", 8000) is False


def test_start_llm_server_skips_when_missing_dir(monkeypatch, tmp_path):
    # If the llm_hosting directory is missing, auto-start should no-op.
    monkeypatch.setattr(run, "_is_port_open", lambda *args, **kwargs: False)
    monkeypatch.setattr(run.os.path, "abspath", lambda p: str(tmp_path / "run.py"))
    run.LLM_PROCESS = None
    run._start_llm_server()
    assert run.LLM_PROCESS is None


def test_start_llm_server_skips_when_port_open(monkeypatch):
    # If the port is already open, the server should not be started.
    monkeypatch.setattr(run, "_is_port_open", lambda *a, **k: True)
    monkeypatch.setattr(run.subprocess, "Popen", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("should not start")))
    run.LLM_PROCESS = None
    run._start_llm_server()
    assert run.LLM_PROCESS is None


def test_start_llm_server_launches(monkeypatch, tmp_path):
    # Simulate a launch by providing a fake Popen object and a temp llm_hosting dir.
    llm_dir = tmp_path / "llm_hosting"
    llm_dir.mkdir()

    monkeypatch.setattr(run, "_is_port_open", lambda *args, **kwargs: False)
    monkeypatch.setattr(run.os.path, "abspath", lambda p: str(tmp_path / "run.py"))

    class DummyProc:
        def __init__(self):
            self.pid = 1234

        def poll(self):
            return None

    def fake_popen(cmd, cwd, env, stdout, stderr):
        # Validate we would have launched in the expected directory.
        assert cwd == str(llm_dir)
        return DummyProc()

    monkeypatch.setattr(run.subprocess, "Popen", fake_popen)

    run.LLM_PROCESS = None
    run._start_llm_server()
    assert isinstance(run.LLM_PROCESS, DummyProc)


def test_start_llm_server_reports_failed_launch(monkeypatch, tmp_path, capsys):
    # If the subprocess exits immediately, the failure message should print.
    llm_dir = tmp_path / "llm_hosting"
    llm_dir.mkdir()

    monkeypatch.setattr(run, "_is_port_open", lambda *args, **kwargs: False)
    monkeypatch.setattr(run.os.path, "abspath", lambda p: str(tmp_path / "run.py"))

    class DummyProc:
        def poll(self):
            return 1

    monkeypatch.setattr(run.subprocess, "Popen", lambda *a, **k: DummyProc())

    run.LLM_PROCESS = None
    run._start_llm_server()
    out = capsys.readouterr().out
    assert "failed to start" in out.lower()


def test_wait_for_llm_ready_true(monkeypatch):
    # Return a mock response with status 200 to simulate readiness.
    class DummyResp:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return b""

    monkeypatch.setattr(run.urllib.request, "urlopen", lambda *args, **kwargs: DummyResp())
    assert run._wait_for_llm_ready(timeout_seconds=1) is True


def test_wait_for_llm_ready_false_on_error(monkeypatch):
    # Force urlopen to raise an error so the readiness loop fails fast.
    def _raise(*args, **kwargs):
        raise run.urllib.error.URLError("fail")

    monkeypatch.setattr(run.urllib.request, "urlopen", _raise)
    # Use a zero timeout to avoid sleeping during the test.
    assert run._wait_for_llm_ready(timeout_seconds=0) is False


def test_wait_for_llm_ready_sleeps_on_exception(monkeypatch):
    # Exercise the exception + sleep branch once.
    def _raise(*args, **kwargs):
        raise run.urllib.error.URLError("fail")

    sleep_calls = {"count": 0}

    monkeypatch.setattr(run.urllib.request, "urlopen", _raise)
    monkeypatch.setattr(run.time, "sleep", lambda *_: sleep_calls.update(count=sleep_calls["count"] + 1))

    # First call sets deadline, second enters loop, third exits.
    times = iter([0.0, 0.0, 2.0])
    monkeypatch.setattr(run.time, "time", lambda: next(times))

    assert run._wait_for_llm_ready(timeout_seconds=1) is False
    assert sleep_calls["count"] == 1


def test_stop_llm_server_terminates(monkeypatch):
    # Provide a fake process to ensure terminate() is called.
    calls = {"terminated": 0}

    class DummyProc:
        def poll(self):
            return None

        def terminate(self):
            calls["terminated"] += 1

    run.LLM_PROCESS = DummyProc()
    run._stop_llm_server()
    assert calls["terminated"] == 1


def test_run_main_block(monkeypatch):
    # Execute run.py as __main__ to cover the entrypoint logic.
    import runpy
    import os
    import socket
    import urllib.request
    import time as time_mod
    import flask

    # Avoid real server start and long waits.
    monkeypatch.setattr(flask.Flask, "run", lambda *a, **k: None)
    monkeypatch.setattr(socket, "create_connection", lambda *a, **k: (_ for _ in ()).throw(OSError("closed")))
    monkeypatch.setattr(os.path, "isdir", lambda *_: False)

    # Force /ready checks to fail quickly.
    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: (_ for _ in ()).throw(run.urllib.error.URLError("fail")))
    t0 = time_mod.time()
    times = iter([t0, t0 + 200])
    monkeypatch.setattr(time_mod, "time", lambda: next(times))
    monkeypatch.setattr(time_mod, "sleep", lambda *_: None)

    root = Path(__file__).resolve().parents[1]
    runpy.run_path(str(root / "src" / "run.py"), run_name="__main__")
