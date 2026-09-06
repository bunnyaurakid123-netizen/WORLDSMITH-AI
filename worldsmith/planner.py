from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Callable

from worldsmith.ai.orchestrator import Ensemble, EnsembleResult
from worldsmith.generation.quality import inspect_plan, repair_plan


@dataclass
class PlanResult:
    plan: dict
    ensemble: EnsembleResult
    quality_issues: tuple = ()

    def pretty(self):
        payload = dict(self.plan)
        if self.quality_issues:
            payload["_quality_review"] = [issue.__dict__ for issue in self.quality_issues]
        return json.dumps(payload, indent=2)


class Planner:
    def __init__(self, ensemble: Ensemble):
        self.ensemble = ensemble

    def make_plan(self, request, context, center=(0, 100, 0), activity: Callable[[str], None] | None = None):
        result = self.ensemble.plan(request, context, center, activity=activity)
        sanitized = self._sanitize(result.plan, center)
        repaired, issues = repair_plan(sanitized)
        if activity and issues:
            activity(f"Quality AI • found {len(issues)} layout issue(s); applied deterministic repairs")
        return PlanResult(repaired, result, tuple(issues))

    @staticmethod
    def _int(value, default):
        try:
            return int(value)
        except (TypeError, ValueError):
            return int(default)

    @staticmethod
    def _clamp_coordinate(value, center_value, radius=256):
        return max(center_value - radius, min(center_value + radius, int(value)))

    def _sanitize(self, plan, center):
        if not isinstance(plan, dict):
            plan = {}
        cx, cy, cz = [int(v) for v in center]
        plan.setdefault("center", [cx, cy, cz])
        if not isinstance(plan["center"], list) or len(plan["center"]) != 3:
            plan["center"] = [cx, cy, cz]
        plan["center"] = [self._int(v, d) for v, d in zip(plan["center"], (cx, cy, cz))]
        plan["seed"] = self._int(plan.get("seed", 1337), 1337)

        terrain = plan.setdefault("terrain", {"enabled": True, "radius": 96, "mountain_height": 80, "roughness": 1.0, "water": True, "vegetation": True})
        terrain["enabled"] = bool(terrain.get("enabled", True)); terrain["water"] = bool(terrain.get("water", True)); terrain["vegetation"] = bool(terrain.get("vegetation", True))
        terrain["radius"] = max(32, min(self._int(terrain.get("radius", 96), 96), 128))
        terrain["mountain_height"] = max(8, min(self._int(terrain.get("mountain_height", 80), 80), 120))
        try:
            terrain["roughness"] = max(0.35, min(float(terrain.get("roughness", 1.0)), 1.8))
        except (TypeError, ValueError):
            terrain["roughness"] = 1.0

        builds = []
        for raw in list(plan.get("builds", []))[:24]:
            if not isinstance(raw, dict): continue
            build = dict(raw)
            for key, default in [("x", cx), ("y", cy + 3), ("z", cz), ("width", 10), ("depth", 10), ("height", 10)]:
                build[key] = self._int(build.get(key, default), default)
            build["x"] = self._clamp_coordinate(build["x"], cx); build["y"] = max(-64, min(320, build["y"])); build["z"] = self._clamp_coordinate(build["z"], cz)
            for key in ("width", "depth", "height"): build[key] = max(5, min(build[key], 64))
            build["type"] = str(build.get("type", "house"))[:40]; build["style"] = str(build.get("style", "natural medieval"))[:100]
            build["interior"] = bool(build.get("interior", True)); build["redstone"] = bool(build.get("redstone", False)); builds.append(build)
        plan["builds"] = builds

        roads = []
        for raw in list(plan.get("roads", []))[:48]:
            if not isinstance(raw, dict): continue
            road = dict(raw)
            for key, default in [("x1", cx), ("z1", cz), ("x2", cx), ("z2", cz), ("y", cy + 4), ("width", 3)]: road[key] = self._int(road.get(key, default), default)
            road["x1"] = self._clamp_coordinate(road["x1"], cx); road["x2"] = self._clamp_coordinate(road["x2"], cx); road["z1"] = self._clamp_coordinate(road["z1"], cz); road["z2"] = self._clamp_coordinate(road["z2"], cz); road["y"] = max(-64, min(320, road["y"])); road["width"] = max(1, min(road["width"], 5)); roads.append(road)
        plan["roads"] = roads

        bridges = []
        for raw in list(plan.get("bridges", []))[:16]:
            if not isinstance(raw, dict): continue
            bridge = dict(raw)
            for key, default in [("x", cx), ("y", cy + 4), ("z", cz), ("x2", cx + 20), ("z2", cz), ("width", 3)]: bridge[key] = self._int(bridge.get(key, default), default)
            bridge["x"] = self._clamp_coordinate(bridge["x"], cx); bridge["x2"] = self._clamp_coordinate(bridge["x2"], cx); bridge["z"] = self._clamp_coordinate(bridge["z"], cz); bridge["z2"] = self._clamp_coordinate(bridge["z2"], cz); bridge["y"] = max(-64, min(320, bridge["y"])); bridge["width"] = max(2, min(bridge["width"], 7)); bridge["type"] = str(bridge.get("type", "stone_bridge"))[:40]; bridges.append(bridge)
        plan["bridges"] = bridges

        operations = []
        for raw in list(plan.get("operations", []))[:48]:
            if not isinstance(raw, dict): continue
            op = dict(raw); op["op"] = str(op.get("op", ""))[:20].lower()
            if op["op"] not in {"fill_box", "hollow_box", "sphere", "cylinder"}: continue
            op["block"] = str(op.get("block", "stone"))[:80]
            for key, default in [("x", cx), ("y", cy), ("z", cz), ("x1", cx), ("y1", cy), ("z1", cz), ("x2", cx), ("y2", cy), ("z2", cz)]:
                op[key] = self._int(op.get(key, default), default)
                if key.startswith("x"): op[key] = self._clamp_coordinate(op[key], cx, 128)
                if key.startswith("z"): op[key] = self._clamp_coordinate(op[key], cz, 128)
                if key.startswith("y"): op[key] = max(-64, min(320, op[key]))
            op["radius"] = max(1, min(self._int(op.get("radius", 4), 4), 32)); op["height"] = max(1, min(self._int(op.get("height", 8), 8), 64))
            volume = (abs(op["x2"] - op["x1"]) + 1) * (abs(op["y2"] - op["y1"]) + 1) * (abs(op["z2"] - op["z1"]) + 1)
            if op["op"] in {"fill_box", "hollow_box"} and volume > 300_000: continue
            operations.append(op)
        plan["operations"] = operations
        plan["notes"] = [str(v)[:200] for v in list(plan.get("notes", []))[:32]]
        return plan
