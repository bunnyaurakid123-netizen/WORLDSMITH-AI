from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path

class WorldDependencyError(RuntimeError): pass

@dataclass
class WorldSummary:
    path: Path
    dimensions: tuple[str,...]
    chunks: int
    bounds: str
    platform: str
    version: str

class WorldEditor:
    def __init__(self,path:Path): self.path=path; self.level=None
    def open(self)->WorldSummary:
        try: import amulet
        except ImportError as exc: raise WorldDependencyError("amulet-core is not installed. Run: pip install -r requirements.txt") from exc
        self.level=amulet.load_level(str(self.path)); wrapper=self.level.level_wrapper
        try: chunks=len(list(self.level.all_chunk_coords("minecraft:overworld")))
        except Exception: chunks=0
        try: bounds=str(self.level.bounds("minecraft:overworld"))
        except Exception: bounds="unavailable"
        return WorldSummary(self.path,tuple(self.level.dimensions),chunks,bounds,str(getattr(wrapper,"platform","unknown")),str(getattr(wrapper,"max_world_version","unknown")))
    def close(self):
        if self.level is not None: self.level.close(); self.level=None
    def save(self):
        if self.level is None: raise RuntimeError("World is not open")
        self.level.save()
    def require_level(self):
        if self.level is None: raise RuntimeError("World is not open")
        return self.level
    def __enter__(self): self.open(); return self
    def __exit__(self,*args): self.close()
