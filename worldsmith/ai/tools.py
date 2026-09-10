from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from worldsmith.analysis.spatial import analyze_save
from worldsmith.generation.quality import inspect_plan, repair_plan
from worldsmith.scanner import SaveInfo, scan_saves


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    handler: Callable
    read_only: bool = True


class AgentTools:
    """Small, explicit tool registry exposed to the WorldSmith agent."""

    def __init__(self):
        self._tools = {
            "scan_saves": ToolSpec("scan_saves", "Find Minecraft Java saves in known locations.", self.scan_saves),
            "inspect_world": ToolSpec("inspect_world", "Analyze a selected save region for terrain, water, vegetation and density.", self.inspect_world),
            "inspect_plan": ToolSpec("inspect_plan", "Run deterministic pre-build quality checks on a plan.", self.inspect_plan),
            "repair_plan": ToolSpec("repair_plan", "Apply only low-risk deterministic corrections to a plan.", self.repair_plan),
        }

    def names(self) -> tuple[str, ...]:
        return tuple(self._tools)

    def call(self, name: str, **kwargs):
        spec = self._tools.get(name)
        if spec is None:
            raise KeyError(f"Unknown WorldSmith tool: {name}")
        return spec.handler(**kwargs)

    @staticmethod
    def scan_saves(extra_dirs: list[Path] | None = None) -> list[SaveInfo]:
        return scan_saves(extra_dirs)

    @staticmethod
    def inspect_world(world_path: Path, center: tuple[int, int, int] = (0, 100, 0), radius: int = 32):
        snapshot = analyze_save(Path(world_path), center, radius=radius)
        return snapshot.text() if snapshot else "No spatial analysis was available."

    @staticmethod
    def inspect_plan(plan: dict):
        return [issue.__dict__ for issue in inspect_plan(plan)]

    @staticmethod
    def repair_plan(plan: dict):
        repaired, issues = repair_plan(plan)
        return {"plan": repaired, "issues": [issue.__dict__ for issue in issues]}
