from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path


def _backup_root(world_path: Path, root: Path | None = None) -> Path:
    root = root or world_path.parent / "backups"
    root.mkdir(parents=True, exist_ok=True)
    return root


def backup_world(world_path: Path, root: Path | None = None) -> Path:
    """Create an independent timestamped snapshot of a Minecraft save."""
    world_path = Path(world_path).resolve()
    if not world_path.is_dir():
        raise FileNotFoundError(f"World directory not found: {world_path}")
    root = _backup_root(world_path, root)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    target = root / f"{world_path.name}-{stamp}"
    shutil.copytree(world_path, target)
    return target


def list_backups(world_path: Path, root: Path | None = None) -> list[Path]:
    world_path = Path(world_path).resolve()
    root = _backup_root(world_path, root)
    prefix = f"{world_path.name}-"
    return sorted((path for path in root.iterdir() if path.is_dir() and path.name.startswith(prefix)), key=lambda p: p.stat().st_mtime, reverse=True)


def restore_world(world_path: Path, backup_path: Path, confirm: bool = False) -> None:
    """Restore a save directory from a snapshot. Caller must ensure Minecraft is closed."""
    if not confirm:
        raise PermissionError("Restoring a world requires explicit confirmation")
    world_path = Path(world_path).resolve()
    backup_path = Path(backup_path).resolve()
    if not world_path.is_dir():
        raise FileNotFoundError(f"World directory not found: {world_path}")
    if not backup_path.is_dir():
        raise FileNotFoundError(f"Backup directory not found: {backup_path}")
    temp = world_path.with_name(world_path.name + ".worldsmith-restore")
    if temp.exists():
        shutil.rmtree(temp)
    shutil.copytree(backup_path, temp)
    try:
        # Swap through a temporary copy to avoid leaving a partially copied save on errors.
        shutil.rmtree(world_path)
        temp.rename(world_path)
    except Exception:
        if world_path.exists():
            shutil.rmtree(world_path)
        if temp.exists():
            temp.rename(world_path)
        raise
