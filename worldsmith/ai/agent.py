from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from worldsmith.backup import backup_world
from worldsmith.generation.builder import WorldBuilder
from worldsmith.generation.postcheck import PostBuildVerifier
from worldsmith.memory import MemoryStore
from worldsmith.planner import PlanResult, Planner
from worldsmith.scanner import SaveInfo
from worldsmith.world import WorldEditor


Activity = Callable[[str], None]


@dataclass
class AgentRun:
    request: str
    world_path: Path
    center: tuple[int, int, int]
    plan: dict = field(default_factory=dict)
    summary: dict = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    activity: list[str] = field(default_factory=list)
    backup: Path | None = None
    verification: object | None = None
    status: str = "created"
    elapsed_seconds: float = 0.0

    def emit(self, message: str, callback: Activity | None = None) -> None:
        self.activity.append(message)
        if callback:
            callback(message)


class WorldSmithAgent:
    """End-to-end safe agent: inspect -> plan -> validate -> execute -> verify."""

    def __init__(
        self,
        planner: Planner,
        memory: MemoryStore | None = None,
        auto_backup: bool = True,
        protect_player_builds: bool = True,
    ):
        self.planner = planner
        self.memory = memory
        self.auto_backup = bool(auto_backup)
        self.protect_player_builds = bool(protect_player_builds)

    @staticmethod
    def _context(world_path: Path) -> str:
        try:
            with WorldEditor(world_path) as editor:
                summary = editor.open()
                return (
                    f"World path: {world_path}\n"
                    f"Platform: {summary.platform}\n"
                    f"Version: {summary.version}\n"
                    f"Dimensions: {', '.join(summary.dimensions)}\n"
                    f"Chunks: {summary.chunks}\n"
                    f"Bounds: {summary.bounds}"
                )
        except Exception as exc:
            return f"World path: {world_path}\nWorld inspection unavailable: {exc}"

    def plan(
        self,
        request: str,
        world_path: Path,
        center: tuple[int, int, int] = (0, 100, 0),
        activity: Activity | None = None,
    ) -> AgentRun:
        run = AgentRun(request=request, world_path=Path(world_path), center=tuple(map(int, center)))
        started = time.perf_counter()
        try:
            run.emit("Agent • inspecting world metadata", activity)
            context = self._context(run.world_path)
            if self.memory:
                memory_context = self.memory.build_context(request, str(run.world_path))
                context += "\n\nLONG-TERM MEMORY:\n" + memory_context
            context += "\n\nPLAYER BUILD PROTECTION=" + str(self.protect_player_builds)
            result: PlanResult = self.planner.make_plan(request, context, run.center, activity=lambda m: run.emit(m, activity))
            run.plan = result.plan
            run.summary = {
                "quality_issues": [issue.__dict__ for issue in result.quality_issues],
                "providers": result.plan.get("_ensemble", []),
                "judge": result.plan.get("_judge", ""),
                "candidate_scores": result.plan.get("_candidate_scores", {}),
                "builds": len(result.plan.get("builds", [])),
                "roads": len(result.plan.get("roads", [])),
                "bridges": len(result.plan.get("bridges", [])),
                "operations": len(result.plan.get("operations", [])),
            }
            run.status = "planned"
            run.emit("Agent • plan validated and ready", activity)
            if self.memory:
                try:
                    self.memory.save_conversation(str(run.world_path), request, str(run.plan.get("summary", "WorldSmith plan")))
                except Exception:
                    pass
        except Exception as exc:
            run.status = "failed"
            run.errors.append(str(exc))
            run.emit(f"Agent • planning failed: {exc}", activity)
        finally:
            run.elapsed_seconds = time.perf_counter() - started
        return run

    def execute(
        self,
        run: AgentRun,
        activity: Activity | None = None,
    ) -> AgentRun:
        if not run.plan:
            run.status = "failed"
            run.errors.append("No plan available")
            return run
        started = time.perf_counter()
        editor = None
        try:
            if self.auto_backup:
                run.emit("Agent • creating non-destructive backup", activity)
                run.backup = backup_world(run.world_path)
            run.emit("Agent • opening Minecraft save", activity)
            editor = WorldEditor(run.world_path)
            editor.open()
            run.emit("Agent • executing world generation", activity)
            result = WorldBuilder(editor.require_level(), seed=int(run.plan.get("seed", 1337))).build(run.plan)
            editor.save()
            run.emit("Agent • save committed", activity)
            editor.close()
            editor = None
            run.emit("Agent • running post-build verification", activity)
            run.verification = PostBuildVerifier(WorldEditor(run.world_path).require_level()).verify(run.plan) if False else None
            # Re-open for factual verification; do not reuse a closed level handle.
            verifier_editor = WorldEditor(run.world_path)
            verifier_editor.open()
            try:
                run.verification = PostBuildVerifier(verifier_editor.require_level()).verify(run.plan)
            finally:
                verifier_editor.close()
            issues = list(getattr(run.verification, "issues", []))
            run.summary.update({
                "blocks_changed": int(getattr(result, "blocks_changed", 0)),
                "structures_changed": int(getattr(result, "structures_changed", 0)),
                "interiors_changed": int(getattr(result, "interiors_changed", 0)),
                "roads_changed": int(getattr(result, "roads_changed", 0)),
                "redstone_blocks": int(getattr(result, "systems_changed", 0)),
                "verification_passed": not issues,
                "verification_issues": [getattr(i, "message", str(i)) for i in issues],
            })
            if issues:
                run.status = "needs-repair"
                run.emit(f"Agent • verification found {len(issues)} issue(s)", activity)
            else:
                run.status = "completed"
                run.emit("Agent • generation verified successfully", activity)
        except Exception as exc:
            run.status = "failed"
            run.errors.append(str(exc))
            run.emit(f"Agent • execution failed: {exc}", activity)
        finally:
            if editor is not None:
                try:
                    editor.close()
                except Exception:
                    pass
            run.elapsed_seconds += time.perf_counter() - started
        return run

    @staticmethod
    def export_run(run: AgentRun, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "request": run.request,
            "world_path": str(run.world_path),
            "center": list(run.center),
            "plan": run.plan,
            "summary": run.summary,
            "errors": run.errors,
            "activity": run.activity,
            "backup": str(run.backup) if run.backup else None,
            "status": run.status,
            "elapsed_seconds": run.elapsed_seconds,
        }
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return path
