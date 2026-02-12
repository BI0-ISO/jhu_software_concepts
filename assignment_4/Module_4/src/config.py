"""
Centralized configuration for Module 3.

This module consolidates environment-driven settings so they are consistent
across the scraper, web app, and database utilities.
"""

from __future__ import annotations

import os


BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_DIR = os.path.join(BASE_DIR, "db")

# Pull configuration
TARGET_NEW_RECORDS = int(os.getenv("TARGET_NEW_RECORDS", "100"))
PULL_MAX_SECONDS = int(os.getenv("PULL_MAX_SECONDS", "600"))

# LLM configuration
LLM_HOST = os.getenv("LLM_HOST", "127.0.0.1")
LLM_PORT = int(os.getenv("LLM_PORT", "8000"))
LLM_HOST_URL = os.getenv("LLM_HOST_URL", f"http://{LLM_HOST}:{LLM_PORT}/standardize")
LLM_TIMEOUT = float(os.getenv("LLM_TIMEOUT", "60"))
LLM_BATCH_SIZE = int(os.getenv("LLM_BATCH_SIZE", "8"))
