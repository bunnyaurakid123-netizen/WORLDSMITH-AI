from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class Settings:
    openai_key: str = ""
    gemini_key: str = ""
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "gemma3"
    openai_model: str = "gpt-5"
    gemini_model: str = "gemini-3.8-flash"
    auto_backup: bool = True
    protect_player_builds: bool = True
    default_radius: int = 96
    google_client_secret: str = ""
    google_name: str = ""
    google_email: str = ""

    @classmethod
    def load(cls, path: Path) -> "Settings":
        if not path.exists():
            return cls()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
        except (OSError, ValueError, TypeError):
            return cls()

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")

    def apply_env(self) -> None:
        self.openai_key = self.openai_key or os.getenv("OPENAI_API_KEY", "")
        self.gemini_key = self.gemini_key or os.getenv("GEMINI_API_KEY", "")
        self.ollama_url = os.getenv("OLLAMA_BASE_URL", self.ollama_url).rstrip("/")
        self.ollama_model = os.getenv("OLLAMA_MODEL", self.ollama_model)
