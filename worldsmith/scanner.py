from __future__ import annotations

import os
import platform
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class SaveInfo:
    name: str
    path: Path
    level_dat: bool
    region_dir: bool
    last_modified: float
    source: str = "Minecraft"


def candidate_saves_dirs() -> list[Path]:
    home = Path.home(); out: list[Path] = []
    if os.getenv("APPDATA"): out.append(Path(os.environ["APPDATA"]) / ".minecraft" / "saves")
    if platform.system() == "Windows":
        out += [home/"AppData/Roaming/.minecraft/saves", home/"AppData/Roaming/.tlauncher/legacy/Minecraft/game/saves"]
    else:
        out += [home/".minecraft/saves", home/".tlauncher/legacy/Minecraft/game/saves"]
    # Launcher-specific locations; only existing folders are returned.
    out += [home/"AppData/Roaming/PrismLauncher/instances", home/"AppData/Roaming/MultiMC/instances", home/"AppData/Roaming/ATLauncher/instances"]
    seen=set(); result=[]
    for p in out:
        try: p=p.expanduser().resolve()
        except OSError: continue
        if p not in seen and p.exists(): seen.add(p); result.append(p)
    return result


def _walk_for_saves(root: Path, max_depth: int = 5):
    if not root.is_dir(): return
    queue=[(root,0)]; seen=set()
    while queue:
        folder, depth=queue.pop(0)
        try: folder=folder.resolve()
        except OSError: continue
        if folder in seen or depth>max_depth: continue
        seen.add(folder)
        try:
            children=list(folder.iterdir())
        except OSError: continue
        if (folder/"level.dat").is_file() or (folder/"region").is_dir():
            yield folder; continue
        if depth < max_depth:
            for child in children:
                if child.is_dir() and child.name not in {"logs","mods","resourcepacks","libraries","versions"}:
                    queue.append((child, depth+1))


def scan_saves(extra_dirs: list[Path] | None = None) -> list[SaveInfo]:
    roots = candidate_saves_dirs() + [Path(p).expanduser() for p in (extra_dirs or [])]
    unique: dict[Path, SaveInfo] = {}
    for root in roots:
        candidates = [root] if root.name.lower() == "saves" else list(_walk_for_saves(root))
        for entry in candidates:
            try:
                ld=(entry/"level.dat").is_file(); rd=(entry/"region").is_dir()
                if not ld and not rd: continue
                modified=entry.stat().st_mtime
                try: modified=max(modified, *(p.stat().st_mtime for p in entry.iterdir()))
                except (OSError,ValueError): pass
                source="Minecraft" if ".minecraft" in str(entry).lower() else "Launcher"
                unique[entry.resolve()]=SaveInfo(entry.name, entry.resolve(), ld, rd, modified, source)
            except OSError: continue
    return sorted(unique.values(), key=lambda s:(s.name.casefold(), str(s.path).casefold()))
