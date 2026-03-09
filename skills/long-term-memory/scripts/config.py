#!/usr/bin/env python3
"""Configuration for long-term memory system."""

import os
import json

BASE_DIR = os.path.expanduser("~/.agents/long-term-memory")
DB_PATH = os.path.join(BASE_DIR, "memory.db")
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
SETUP_COMPLETE = os.path.join(BASE_DIR, ".setup_complete")
SETUP_IN_PROGRESS = os.path.join(BASE_DIR, ".setup_in_progress")

PROFILES = {
    "light": {
        "model_name": "BAAI/bge-small-zh-v1.5",
        "embedding_dim": 512,
    },
    "standard": {
        "model_name": "BAAI/bge-m3",
        "embedding_dim": 1024,
    },
}


def load_config():
    """Load config from ~/.agents/long-term-memory/config.json."""
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH) as f:
            return json.load(f)
    return None


def save_config(config):
    """Save config to disk."""
    os.makedirs(BASE_DIR, exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def get_venv_python():
    return os.path.join(BASE_DIR, ".venv", "bin", "python")


def is_setup_complete():
    return os.path.exists(SETUP_COMPLETE)
