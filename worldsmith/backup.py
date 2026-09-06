from __future__ import annotations
import shutil
from datetime import datetime
from pathlib import Path

def backup_world(world_path: Path, root: Path | None = None) -> Path:
    root = root or world_path.parent / "backups"
    root.mkdir(parents=True, exist_ok=True)
    target = root / f"{world_path.name}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    shutil.copytree(world_path, target)
    return target
