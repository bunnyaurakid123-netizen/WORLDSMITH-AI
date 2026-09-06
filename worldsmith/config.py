from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path

from worldsmith.secrets import SecretStore


@dataclass
class Settings:
    openai_key: str = ""
    gemini_key: str = ""
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "gemma3"
    openai_model: str = "gpt-5.1"
    gemini_model: str = "gemini-3.7-flash"
    auto_backup: bool = True
    protect_player_builds: bool = True
    default_radius: int = 96
    google_client_secret: str = ""
    google_name: str = ""
    google_email: str = ""

    @classmethod
    def load(cls, path: Path) -> "Settings":
        if not path.exists():
            settings = cls()
        else:
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                settings = cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__ and k not in {"openai_key", "gemini_key"}})
                legacy_openai = str(data.get("openai_key", ""))
                legacy_gemini = str(data.get("gemini_key", ""))
                if legacy_openai:
                    SecretStore.set("openai", legacy_openai)
                if legacy_gemini:
                    SecretStore.set("gemini", legacy_gemini)
            except (OSError, ValueError, TypeError):
                settings = cls()
        settings.openai_key = SecretStore.get("openai")
        settings.gemini_key = SecretStore.get("gemini")
        return settings

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        data = asdict(self)
        openai_key = str(data.pop("openai_key", ""))
        gemini_key = str(data.pop("gemini_key", ""))
        SecretStore.set("openai", openai_key)
        SecretStore.set("gemini", gemini_key)
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def apply_env(self) -> None:
        self.openai_key = os.getenv("OPENAI_API_KEY", "") or SecretStore.get("openai")
        self.gemini_key = os.getenv("GEMINI_API_KEY", "") or SecretStore.get("gemini")
        self.ollama_url = os.getenv("OLLAMA_BASE_URL", self.ollama_url).rstrip("/")
        self.ollama_model = os.getenv("OLLAMA_MODEL", self.ollama_model)
