import atexit
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

from flask import Flask
from M1_material.board import bp as m1_bp
from M3_material.board import bp as m3_bp

app = Flask(__name__)

# Register both blueprints
app.register_blueprint(m1_bp)
app.register_blueprint(m3_bp)

LLM_PROCESS = None


def _is_port_open(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=0.5):
            return True
    except OSError:
        return False


def _start_llm_server():
    global LLM_PROCESS
    host = os.getenv("LLM_HOST", "127.0.0.1")
    port = int(os.getenv("LLM_PORT", "8000"))
    if _is_port_open(host, port):
        return
    base_dir = os.path.dirname(os.path.abspath(__file__))
    llm_dir = os.path.join(base_dir, "llm_hosting")
    if not os.path.isdir(llm_dir):
        print("LLM server folder not found. Skipping auto-start.")
        return
    cmd = [sys.executable, "app.py", "--serve"]
    env = os.environ.copy()
    env.setdefault("MODEL_FILE", "tinyllama-1.1b-chat-v1.0.Q3_K_M.gguf")
    env.setdefault("N_CTX", "1024")
    env.setdefault("N_THREADS", str(min(4, os.cpu_count() or 2)))
    log_path = os.path.join(llm_dir, "llm_server.log")
    log_file = open(log_path, "a")
    LLM_PROCESS = subprocess.Popen(cmd, cwd=llm_dir, env=env, stdout=log_file, stderr=log_file)
    if LLM_PROCESS.poll() is not None:
        print("LLM server failed to start. Check llm_hosting/llm_server.log.")


def _wait_for_llm_ready(timeout_seconds: int = 180) -> bool:
    host = os.getenv("LLM_HOST", "127.0.0.1")
    port = int(os.getenv("LLM_PORT", "8000"))
    url = f"http://{host}:{port}/ready"
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=10) as resp:
                if resp.status == 200:
                    return True
        except (urllib.error.URLError, ConnectionError):
            time.sleep(1)
    return False


def _stop_llm_server():
    if LLM_PROCESS and LLM_PROCESS.poll() is None:
        LLM_PROCESS.terminate()


atexit.register(_stop_llm_server)

if __name__ == "__main__":
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true" or not app.debug:
        _start_llm_server()
        if not _wait_for_llm_ready():
            print("LLM server did not become ready in time. Check llm_hosting/llm_server.log.")
    app.run(debug=True, host="0.0.0.0", port=8080)
