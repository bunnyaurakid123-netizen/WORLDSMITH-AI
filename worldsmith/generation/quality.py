from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class QualityIssue:
    severity: str
    message: str
    repair: str


def _distance(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def inspect_plan(plan: dict) -> list[QualityIssue]:
    """Heuristic pre-build review for common layout failures."""
    issues: list[QualityIssue] = []
    builds = [b for b in plan.get("builds", []) if isinstance(b, dict)]
    center = plan.get("center", [0, 100, 0])

    if not builds:
        issues.append(QualityIssue("warning", "Plan has no major structures", "Add at least one purposeful landmark or settlement."))
        return issues

    positions = [(int(b.get("x", center[0])), int(b.get("z", center[2]))) for b in builds]
    max_distance = max((_distance((center[0], center[2]), p) for p in positions), default=0)
    if len(builds) >= 4 and max_distance < 12:
        issues.append(QualityIssue("warning", "Major structures are clustered too tightly", "Spread major structures into districts or a deliberate radial layout."))

    has_large = any(max(int(b.get("width", 0)), int(b.get("depth", 0))) >= 24 for b in builds)
    if len(builds) >= 6 and not has_large:
        issues.append(QualityIssue("info", "Settlement lacks a dominant landmark", "Promote a castle, hall, temple, tower, bridge, or civic building."))

    interiors = sum(bool(b.get("interior", False)) for b in builds)
    if len(builds) >= 3 and interiors < max(1, len(builds) // 3):
        issues.append(QualityIssue("warning", "Few buildings request interiors", "Enable interiors on important structures and civic buildings."))

    redstone = sum(bool(b.get("redstone", False)) for b in builds)
    if any(str(b.get("type", "")).lower() in {"castle", "fortress", "keep"} for b in builds) and redstone == 0:
        issues.append(QualityIssue("info", "Fortified structures have no redstone intent", "Consider gates, alarms, hidden entrances, or defensive mechanisms."))

    if not plan.get("roads") and len(builds) >= 2:
        issues.append(QualityIssue("warning", "Multiple structures have no road network", "Add roads or paths connecting the main destinations."))

    if len(plan.get("bridges", [])) == 0 and plan.get("roads"):
        water = bool(plan.get("terrain", {}).get("water", True))
        if water and len(builds) >= 5:
            issues.append(QualityIssue("info", "Water is enabled but no bridge is planned", "Add bridges where roads cross rivers or ravines."))

    return issues


def repair_plan(plan: dict) -> tuple[dict, list[QualityIssue]]:
    """Apply deterministic low-risk repairs to a plan without inventing whole regions."""
    repaired = dict(plan)
    issues = inspect_plan(repaired)
    builds = [dict(b) for b in repaired.get("builds", []) if isinstance(b, dict)]
    center = repaired.get("center", [0, 100, 0])

    if len(builds) >= 2 and not repaired.get("roads"):
        roads = []
        anchor = builds[0]
        for target in builds[1:8]:
            roads.append({
                "x1": int(anchor.get("x", center[0])),
                "z1": int(anchor.get("z", center[2])),
                "x2": int(target.get("x", center[0])),
                "z2": int(target.get("z", center[2])),
                "y": int(target.get("y", center[1])) + 1,
                "width": 2,
            })
        repaired["roads"] = roads

    if builds and any(str(b.get("type", "")).lower() in {"castle", "fortress", "keep"} for b in builds):
        for build in builds:
            if str(build.get("type", "")).lower() in {"castle", "fortress", "keep"}:
                build["interior"] = True
                build["redstone"] = True
                break
    repaired["builds"] = builds
    return repaired, issues
