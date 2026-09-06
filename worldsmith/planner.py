from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Callable

from worldsmith.ai.orchestrator import Ensemble, EnsembleResult


@dataclass
class PlanResult:
    plan: dict
    ensemble: EnsembleResult

    def pretty(self):
        return json.dumps(self.plan, indent=2)


class Planner:
    def __init__(self, ensemble: Ensemble):
        self.ensemble = ensemble

    def make_plan(self, request, context, center=(0, 100, 0), activity: Callable[[str], None] | None = None):
        result = self.ensemble.plan(request, context, center, activity=activity)
        return PlanResult(self._sanitize(result.plan, center), result)

    @staticmethod
    def _int(value, default):
        try:
            return int(value)
        except (TypeError, ValueError):
            return int(default)

    def _sanitize(self, plan, center):
        if not isinstance(plan, dict):
            plan = {}
        cx, cy, cz = [int(v) for v in center]
        plan.setdefault("center", [cx, cy, cz])
        if len(plan["center"]) != 3:
            plan["center"] = [cx, cy, cz]
        plan["seed"] = self._int(plan.get("seed", 1337), 1337)

        terrain = plan.setdefault(
            "terrain",
            {"enabled": True, "radius": 96, "mountain_height": 80, "roughness": 1.0, "water": True, "vegetation": True},
        )
        terrain["enabled"] = bool(terrain.get("enabled", True))
        terrain["water"] = bool(terrain.get("water", True))
        terrain["vegetation"] = bool(terrain.get("vegetation", True))
        terrain["radius"] = max(32, min(self._int(terrain.get("radius", 96), 96), 128))
        terrain["mountain_height"] = max(8, min(self._int(terrain.get("mountain_height", 80), 80), 120))
        try:
            terrain["roughness"] = max(0.35, min(float(terrain.get("roughness", 1.0)), 1.8))
        except (TypeError, ValueError):
            terrain["roughness"] = 1.0

        builds = []
        for raw in list(plan.get("builds", []))[:24]:
            if not isinstance(raw, dict):
                continue
            build = dict(raw)
            for key, default in [("x", cx), ("y", cy + 3), ("z", cz), ("width", 10), ("depth", 10), ("height", 10)]:
                build[key] = self._int(build.get(key, default), default)
            for key in ("width", "depth", "height"):
                build[key] = max(5, min(build[key], 64))
            build["type"] = str(build.get("type", "house"))[:40]
            build["style"] = str(build.get("style", "natural medieval"))[:100]
            build["interior"] = bool(build.get("interior", True))
            build["redstone"] = bool(build.get("redstone", False))
            builds.append(build)
        plan["builds"] = builds

        roads = []
        for raw in list(plan.get("roads", []))[:48]:
            if not isinstance(raw, dict):
                continue
            road = dict(raw)
            for key, default in [("x1", cx), ("z1", cz), ("x2", cx), ("z2", cz), ("y", cy + 4), ("width", 3)]:
                road[key] = self._int(road.get(key, default), default)
            road["width"] = max(1, min(road["width"], 5))
            roads.append(road)
        plan["roads"] = roads

        bridges = []
        for raw in list(plan.get("bridges", []))[:16]:
            if not isinstance(raw, dict):
                continue
            bridge = dict(raw)
            for key, default in [("x", cx), ("y", cy + 4), ("z", cz), ("x2", cx + 20), ("z2", cz), ("width", 3)]:
                bridge[key] = self._int(bridge.get(key, default), default)
            bridge["width"] = max(2, min(bridge["width"], 7))
            bridge["type"] = str(bridge.get("type", "stone_bridge"))[:40]
            bridges.append(bridge)
        plan["bridges"] = bridges

        plan["notes"] = [str(v)[:200] for v in list(plan.get("notes", []))[:32]]
        return plan
