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

def candidate_saves_dirs() -> list[Path]:
    home = Path.home(); candidates=[]
    if os.getenv("APPDATA"): candidates.append(Path(os.environ["APPDATA"]) / ".minecraft" / "saves")
    if platform.system() == "Windows":
        candidates += [home/"AppData/Roaming/.minecraft/saves", home/"AppData/Roaming/.tlauncher/legacy/Minecraft/game/saves"]
    else:
        candidates += [home/".minecraft/saves", home/".tlauncher/legacy/Minecraft/game/saves"]
    out=[]; seen=set()
    for p in candidates:
        try: r=p.expanduser().resolve()
        except OSError: continue
        if r not in seen: seen.add(r); out.append(r)
    return out

def scan_saves(extra_dirs: list[Path] | None = None) -> list[SaveInfo]:
    unique={}
    for saves_dir in candidate_saves_dirs()+[p.resolve() for p in (extra_dirs or [])]:
        try:
            if not saves_dir.is_dir(): continue
            for entry in saves_dir.iterdir():
                if not entry.is_dir(): continue
                ld=(entry/"level.dat").is_file(); rd=(entry/"region").is_dir()
                if not ld and not rd: continue
                try: modified=max(p.stat().st_mtime for p in entry.iterdir())
                except (OSError,ValueError): modified=entry.stat().st_mtime
                unique[entry]=SaveInfo(entry.name,entry,ld,rd,modified)
        except OSError: continue
    return sorted(unique.values(), key=lambda s:s.name.casefold())
