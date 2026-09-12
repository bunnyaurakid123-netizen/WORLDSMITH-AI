from __future__ import annotations

import json
import os
from pathlib import Path

CONFIG_DIR = Path(os.getenv("APPDATA", Path.home())) / "WorldSmithAI"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULTS = {
    "openai_model": "gpt-5.6",
    "gemini_model": "gemini-3.8-flash",
    "ollama_model": "gemma3",
    "ollama_url": "http://127.0.0.1:11434",
    "reasoning": "high",
}


def load_config() -> dict:
    data = DEFAULTS.copy()
    try:
        if CONFIG_FILE.is_file(): data.update(json.loads(CONFIG_FILE.read_text(encoding="utf-8")))
    except Exception: pass
    return data


def save_config(data: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps({**DEFAULTS, **data}, indent=2), encoding="utf-8")
