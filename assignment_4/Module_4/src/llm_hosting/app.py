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
    r"(?i)^jhu$": "Johns Hopkins University",
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
    "You are a data cleaning assistant. Standardize degree program and university "
    "names.\n\n"
    "Rules:\n"
    "- Input provides 'program' and 'university' strings.\n"
    "- Trim extra spaces and commas.\n"
    '- Expand obvious abbreviations (e.g., "McG" -> "McGill University", '
    '"UBC" -> "University of British Columbia").\n'
    "- Use Title Case for program; use official capitalization for university "
    "names (e.g., \"University of X\").\n"
    '- Ensure correct spelling.\n'
    '- If university cannot be inferred, fallback to original or "Unknown".\n\n'
    "Return JSON ONLY with keys:\n"
    "  standardized_program, standardized_university\n"
)

FEW_SHOTS: List[Tuple[Dict[str, str], Dict[str, str]]] = [
    (
        {"program": "Information Studies", "university": "McGill University"},
        {
            "standardized_program": "Information Studies",
            "standardized_university": "McGill University",
        },
    ),
    (
        {"program": "Information", "university": "McG"},
        {
            "standardized_program": "Information Studies",
            "standardized_university": "McGill University",
        },
    ),
    (
        {"program": "Mathematics", "university": "University Of British Columbia"},
        {
            "standardized_program": "Mathematics",
            "standardized_university": "University of British Columbia",
        },
    ),
]

_LLM: Llama | None = None

# ---------------- Load LLM ----------------
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

# ---------------- Normalization helpers ----------------
def _best_match(name: str, candidates: List[str], cutoff: float = 0.86) -> str | None:
    if not name or not candidates:
        return None
    matches = difflib.get_close_matches(name, candidates, n=1, cutoff=cutoff)
    return matches[0] if matches else None

def _post_normalize_program(prog: str) -> str:
    p = (prog or "").strip()
    p = COMMON_PROG_FIXES.get(p, p).title()
    match = _best_match(p, CANON_PROGS, 0.84)
    return match or p

def _post_normalize_university(uni: str) -> str:
    u = (uni or "").strip()
    for pat, full in ABBREV_UNI.items():
        if re.fullmatch(pat, u):
            u = full
            break
    u = COMMON_UNI_FIXES.get(u, u)
    if u:
        u = re.sub(r"\bOf\b", "of", u.title())
    match = _best_match(u, CANON_UNIS, 0.86)
    return match or u or "Unknown"

# ---------------- LLM call ----------------
def _call_llm(program_text: str, original_uni: str | None = None) -> Dict[str, str]:
    """
    Standardize program and university.
    Ensures the university is correctly assigned.
    """
    llm = _load_llm()
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    # Few-shot examples
    for x_in, x_out in FEW_SHOTS:
        messages.append({"role": "user", "content": json.dumps(x_in, ensure_ascii=False)})
        messages.append({"role": "assistant", "content": json.dumps(x_out, ensure_ascii=False)})

    # Include both program and original university
    user_input = {"program": program_text, "university": original_uni or ""}
    messages.append({"role": "user", "content": json.dumps(user_input, ensure_ascii=False)})

    try:
        out = llm.create_chat_completion(messages=messages, temperature=0.0, max_tokens=128)
        text = (out["choices"][0]["message"]["content"] or "").strip()
        match = JSON_OBJ_RE.search(text)
        obj = json.loads(match.group(0) if match else text)
        std_prog = str(obj.get("standardized_program", program_text)).strip()
        std_uni = str(obj.get("standardized_university", original_uni or "")).strip()
    except Exception:
        # Fallback
        std_prog = program_text
        std_uni = original_uni or ""

    # Offline post-normalization
    std_prog = _post_normalize_program(std_prog)
    std_uni = _post_normalize_university(std_uni)

    # Final fallback
    if not std_prog:
        std_prog = program_text
    if not std_uni:
        std_uni = original_uni or "Unknown"

    return {"standardized_program": std_prog, "standardized_university": std_uni}

# ---------------- Flask API ----------------
def _normalize_input(payload: Any) -> List[Dict[str, Any]]:
    """Normalize input payload into a list of row dicts."""
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get("rows"), list):
        return payload["rows"]
    return []

@app.get("/")
def health() -> Any:
    """Simple health check."""
    return jsonify({"ok": True})

@app.get("/status")
def status() -> Any:
    """Return whether the model is loaded."""
    return jsonify({"ok": True, "model_loaded": _LLM is not None})

@app.get("/ready")
def ready() -> Any:
    """Force model load and report readiness."""
    _load_llm()
    return jsonify({"ok": True, "model_loaded": True})

@app.post("/standardize")
def standardize() -> Any:
    """Standardize program/university values for a batch of rows."""
    payload = request.get_json(force=True, silent=True)
    rows = _normalize_input(payload)
    out: List[Dict[str, Any]] = []
    for row in rows:
        program_text = row.get("program") or ""
        original_uni = row.get("university") or ""
        result = _call_llm(program_text, original_uni)
        row["llm_generated_program"] = result["standardized_program"]
        row["llm_generated_university"] = result["standardized_university"]
        out.append(row)
    return jsonify({"rows": out})

# ---------------- CLI ----------------
def _cli_process_file(in_path: str, out_path: str | None, append: bool, to_stdout: bool) -> None:
    """CLI helper to standardize a file of rows into JSONL output."""
    with open(in_path, "r", encoding="utf-8") as f:
        rows = _normalize_input(json.load(f))

    sink = sys.stdout if to_stdout else None
    if not to_stdout:
        out_path = out_path or (in_path + ".jsonl")
        mode = "a" if append else "w"
        sink = open(out_path, mode, encoding="utf-8")

    assert sink is not None

    try:
        for i, row in enumerate(rows, start=1):
            program_text = row.get("program") or ""
            original_uni = row.get("university") or ""
            result = _call_llm(program_text, original_uni)
            row["llm_generated_program"] = result["standardized_program"]
            row["llm_generated_university"] = result["standardized_university"]

            json.dump(row, sink, ensure_ascii=False)
            sink.write("\n")
            sink.flush()

            if i % 1000 == 0:
                print(f"Processed {i} rows...", file=sys.stderr)
    finally:
        if sink is not sys.stdout:
            sink.close()

# ---------------- Entry ----------------
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Standardize program/university with a tiny local LLM.")
    parser.add_argument("--file", help="Path to JSON input (list of rows or {'rows': [...]})", default=None)
    parser.add_argument("input_json", nargs="?", help="Positional path to JSON input (optional)")
    parser.add_argument("--serve", action="store_true", help="Run the HTTP server instead of CLI.")
    parser.add_argument("--out", default=None, help="Output path for JSON Lines (ndjson). Defaults to <input>.jsonl when --file is set.")
    parser.add_argument("--append", action="store_true", help="Append to the output file instead of overwriting.")
    parser.add_argument("--stdout", action="store_true", help="Write JSON Lines to stdout instead of a file.")
    args = parser.parse_args()

    input_path = args.file or args.input_json
    if args.serve or input_path is None:
        port = int(os.getenv("PORT", "8000"))
        app.run(host="0.0.0.0", port=port, debug=False)
    else:
        _cli_process_file(
            in_path=input_path,
            out_path=args.out,
            append=bool(args.append),
            to_stdout=bool(args.stdout),
        )
