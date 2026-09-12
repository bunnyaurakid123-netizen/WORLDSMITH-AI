from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path


def worldsmith_saves_dir(base: Path | None = None) -> Path:
    root = Path(base) if base else Path.home() / "WorldSmith AI"
    path = root / ".saves"
    path.mkdir(parents=True, exist_ok=True)
    return path


def import_world_to_workspace(world: Path, base: Path | None = None) -> Path:
    """Copy a Minecraft save into WorldSmith's private .saves workspace.

    The original world is never modified by this function.
    """
    world = Path(world).expanduser().resolve()
    if not (world / "level.dat").is_file(): raise ValueError(f"Not a Minecraft save: {world}")
    dest = worldsmith_saves_dir(base) / world.name
    if dest.exists():
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest = worldsmith_saves_dir(base) / f"{world.name}_import_{stamp}"
    shutil.copytree(world, dest)
    return dest


def refresh_workspace_saves(base: Path | None = None) -> list[Path]:
    root = worldsmith_saves_dir(base)
    return sorted([p for p in root.iterdir() if p.is_dir() and (p / "level.dat").is_file()], key=lambda p:p.name.casefold())
