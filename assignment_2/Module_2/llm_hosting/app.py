# -*- coding: utf-8 -*-
"""Flask + tiny local LLM standardizer with incremental JSONL CLI output."""

from __future__ import annotations

import json
import os
import re
import sys
import difflib
from typing import Any, Dict, List, Tuple

from flask import Flask, jsonify, request
from huggingface_hub import hf_hub_download
from llama_cpp import Llama  # CPU-only by default if N_GPU_LAYERS=0

app = Flask(__name__)

# ---------------- Model config ----------------
MODEL_REPO = os.getenv(
    "MODEL_REPO",
    "TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF",
)
MODEL_FILE = os.getenv(
    "MODEL_FILE",
    "tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf",
)

N_THREADS = int(os.getenv("N_THREADS", str(os.cpu_count() or 2)))
N_CTX = int(os.getenv("N_CTX", "2048"))
N_GPU_LAYERS = int(os.getenv("N_GPU_LAYERS", "0"))  # 0 → CPU-only

CANON_UNIS_PATH = os.getenv("CANON_UNIS_PATH", "canon_universities.txt")
CANON_PROGS_PATH = os.getenv("CANON_PROGS_PATH", "canon_programs.txt")

# Precompiled, non-greedy JSON object matcher to tolerate chatter around JSON
JSON_OBJ_RE = re.compile(r"\{.*?\}", re.DOTALL)

# ---------------- Canonical lists + abbrev maps ----------------
def _read_lines(path: str) -> List[str]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return [ln.strip() for ln in f if ln.strip()]
    except FileNotFoundError:
        return []

CANON_UNIS = _read_lines(CANON_UNIS_PATH)
CANON_PROGS = _read_lines(CANON_PROGS_PATH)

ABBREV_UNI: Dict[str, str] = {
    r"(?i)^mcg(\.|ill)?$": "McGill University",
    r"(?i)^(ubc|u\.?b\.?c\.?)$": "University of British Columbia",
    r"(?i)^uoft$": "University of Toronto",
}

COMMON_UNI_FIXES: Dict[str, str] = {
    "McGiill University": "McGill University",
    "Mcgill University": "McGill University",
    "University Of British Columbia": "University of British Columbia",
}

COMMON_PROG_FIXES: Dict[str, str] = {
    "Mathematic": "Mathematics",
    "Info Studies": "Information Studies",
}

# ---------------- Few-shot prompt ----------------
SYSTEM_PROMPT = (
    "You are a data cleaning assistant. Standardize only the degree program name.\n"
    "DO NOT modify the university. Copy it exactly from input.\n"
    "Rules:\n"
    "- Input provides 'program' (program name) and 'university' (official university name).\n"
    "- Only normalize the program (title-case, spelling fixes, canonical mapping).\n"
    "- Return JSON ONLY with keys:\n"
    "  standardized_program, standardized_university\n"
)

FEW_SHOTS: List[Tuple[Dict[str, str], Dict[str, str]]] = [
    (
        {"program": "Information Studies", "university": "McGill University"},
        {"standardized_program": "Information Studies", "standardized_university": "McGill University"},
    ),
    (
        {"program": "Information", "university": "McGill University"},
        {"standardized_program": "Information Studies", "standardized_university": "McGill University"},
    ),
    (
        {"program": "Mathematics", "university": "University of British Columbia"},
        {"standardized_program": "Mathematics", "standardized_university": "University of British Columbia"},
    ),
]

_LLM: Llama | None = None

def _load_llm() -> Llama:
    global _LLM
    if _LLM is not None:
        return _LLM

    model_path = hf_hub_download(
        repo_id=MODEL_REPO,
        filename=MODEL_FILE,
        local_dir="models",
        local_dir_use_symlinks=False,
        force_filename=MODEL_FILE,
    )

    _LLM = Llama(
        model_path=model_path,
        n_ctx=N_CTX,
        n_threads=N_THREADS,
        n_gpu_layers=N_GPU_LAYERS,
        verbose=False,
    )
    return _LLM

def _split_fallback(program: str, university: str) -> Tuple[str, str]:
    """Rules-first fallback; keeps university immutable."""
    prog = re.sub(r"\s+", " ", (program or "")).strip().strip(",")
    uni = university or "Unknown"
    return prog.title(), uni  # Only normalize program

def _best_match(name: str, candidates: List[str], cutoff: float = 0.86) -> str | None:
    if not name or not candidates:
        return None
    matches = difflib.get_close_matches(name, candidates, n=1, cutoff=cutoff)
    return matches[0] if matches else None

def _post_normalize_program(prog: str) -> str:
    p = (prog or "").strip()
    p = COMMON_PROG_FIXES.get(p, p)
    p = p.title()
    if p in CANON_PROGS:
        return p
    match = _best_match(p, CANON_PROGS, cutoff=0.84)
    return match or p

def _post_normalize_university(uni: str, original_uni: str) -> str:
    """Return original university; only minor formatting if necessary."""
    if not original_uni:
        return uni or "Unknown"
    return original_uni  # Immutable

def _call_llm(program_text: str, university: str) -> Dict[str, str]:
    llm = _load_llm()

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for x_in, x_out in FEW_SHOTS:
        messages.append({"role": "user", "content": json.dumps(x_in, ensure_ascii=False)})
        messages.append({"role": "assistant", "content": json.dumps(x_out, ensure_ascii=False)})

    messages.append({"role": "user", "content": json.dumps({"program": program_text, "university": university}, ensure_ascii=False)})

    out = llm.create_chat_completion(messages=messages, temperature=0.0, max_tokens=128, top_p=1.0)

    text = (out["choices"][0]["message"]["content"] or "").strip()
    try:
        match = JSON_OBJ_RE.search(text)
        obj = json.loads(match.group(0) if match else text)
        std_prog = str(obj.get("standardized_program", "")).strip()
    except Exception:
        std_prog, _ = _split_fallback(program_text, university)

    std_prog = _post_normalize_program(std_prog)
    std_uni = _post_normalize_university(university, university)  # Immutable
    return {"standardized_program": std_prog, "standardized_university": std_uni}

def _normalize_input(payload: Any) -> List[Dict[str, Any]]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get("rows"), list):
        return payload["rows"]
    return []

@app.get("/")
def health() -> Any:
    return jsonify({"ok": True})

@app.post("/standardize")
def standardize() -> Any:
    payload = request.get_json(force=True, silent=True)
    rows = _normalize_input(payload)

    out: List[Dict[str, Any]] = []
    for row in rows:
        program_text = (row or {}).get("program") or ""
        university_text = (row or {}).get("university") or ""
        result = _call_llm(program_text, university_text)
        row["llm-generated-program"] = result["standardized_program"]
        row["llm-generated-university"] = result["standardized_university"]
        out.append(row)

    return jsonify({"rows": out})

def _cli_process_file(in_path: str, out_path: str | None, append: bool, to_stdout: bool) -> None:
    with open(in_path, "r", encoding="utf-8") as f:
        rows = _normalize_input(json.load(f))

    sink = sys.stdout if to_stdout else None
    if not to_stdout:
        out_path = out_path or (in_path + ".jsonl")
        mode = "a" if append else "w"
        sink = open(out_path, mode, encoding="utf-8")

    assert sink is not None

    try:
        for row in rows:
            program_text = (row or {}).get("program") or ""
            university_text = (row or {}).get("university") or ""
            result = _call_llm(program_text, university_text)
            row["llm-generated-program"] = result["standardized_program"]
            row["llm-generated-university"] = result["standardized_university"]

            json.dump(row, sink, ensure_ascii=False)
            sink.write("\n")
            sink.flush()
    finally:
        if sink is not sys.stdout:
            sink.close()

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Standardize program/university with a tiny local LLM.")
    parser.add_argument("--file", help="Path to JSON input", default=None)
    parser.add_argument("--serve", action="store_true", help="Run the HTTP server instead of CLI.")
    parser.add_argument("--out", default=None, help="Output path for JSON Lines (ndjson).")
    parser.add_argument("--append", action="store_true", help="Append to the output file instead of overwriting.")
    parser.add_argument("--stdout", action="store_true", help="Write JSON Lines to stdout instead of a file.")
    args = parser.parse_args()

    if args.serve or args.file is None:
        port = int(os.getenv("PORT", "8000"))
        app.run(host="0.0.0.0", port=port, debug=False)
    else:
        _cli_process_file(in_path=args.file, out_path=args.out, append=bool(args.append), to_stdout=bool(args.stdout))
