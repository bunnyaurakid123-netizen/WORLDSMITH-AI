from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class WorldSmithProject:
    format_version: int = 1
    created_at: str = ""
    updated_at: str = ""
    world_path: str = ""
    prompt: str = ""
    plan: dict[str, Any] = field(default_factory=dict)
    camera: dict[str, float] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def new(cls, world_path: Path | None = None) -> "WorldSmithProject":
        stamp = datetime.now(timezone.utc).isoformat()
        return cls(created_at=stamp, updated_at=stamp, world_path=str(world_path) if world_path else "")

    def save(self, path: Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.updated_at = datetime.now(timezone.utc).isoformat()
        path.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")
        return path

    @classmethod
    def load(cls, path: Path) -> "WorldSmithProject":
        path = Path(path)
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("WorldSmith project must contain a JSON object")
        allowed = {f for f in cls.__dataclass_fields__}
        payload = {key: value for key, value in data.items() if key in allowed}
        project = cls(**payload)
        if project.format_version != 1:
            raise ValueError(f"Unsupported WorldSmith project format: {project.format_version}")
        return project
