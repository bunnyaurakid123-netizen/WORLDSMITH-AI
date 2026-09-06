from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class BuildAudit:
    started_at: str
    finished_at: str = ""
    elapsed_seconds: float = 0.0
    world_path: str = ""
    seed: int = 0
    summary: str = ""
    providers: list[str] = field(default_factory=list)
    judge: str = ""
    blocks_changed: int = 0
    structures_changed: int = 0
    interiors_changed: int = 0
    roads_changed: int = 0
    redstone_blocks: int = 0
    terrain_columns: int = 0
    backup_path: str = ""
    quality_issues: list[dict[str, Any]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    repair_provider: str = ""
    repair_plan_path: str = ""

    @classmethod
    def start(cls, world_path: Path, plan: dict) -> "BuildAudit":
        return cls(
            started_at=datetime.now(timezone.utc).isoformat(),
            world_path=str(world_path),
            seed=int(plan.get("seed", 0)),
            summary=str(plan.get("summary", ""))[:1000],
            providers=[str(p) for p in plan.get("_ensemble", [])],
            judge=str(plan.get("_judge", "")),
        )

    def finish(self, result=None, backup_path: Path | None = None, errors: list[str] | None = None, started_monotonic: float | None = None) -> "BuildAudit":
        self.finished_at = datetime.now(timezone.utc).isoformat()
        self.elapsed_seconds = max(0.0, time.monotonic() - started_monotonic) if started_monotonic is not None else self.elapsed_seconds
        if result is not None:
            for field_name in ("blocks_changed", "structures_changed", "interiors_changed", "roads_changed", "systems_changed", "terrain_columns"):
                value = int(getattr(result, field_name, 0))
                if field_name == "systems_changed":
                    self.redstone_blocks = value
                else:
                    setattr(self, field_name, value)
        if backup_path:
            self.backup_path = str(backup_path)
        if errors:
            self.errors.extend(str(e) for e in errors)
        return self

    def save(self, root: Path | None = None) -> Path:
        root = root or (Path.home() / ".worldsmith" / "runs")
        root.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
        path = root / f"build-{stamp}.json"
        path.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")
        return path
