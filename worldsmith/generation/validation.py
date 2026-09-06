from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Issue:
    severity: str
    message: str


def validate_plan(plan: dict, world_radius: int = 128) -> list[Issue]:
    """Static safety/quality checks performed before a build starts."""
    issues: list[Issue] = []
    center = plan.get("center", [0, 100, 0])
    if not isinstance(center, list) or len(center) != 3:
        issues.append(Issue("error", "center must contain exactly three coordinates"))
        return issues

    builds = plan.get("builds", [])
    boxes: list[tuple[int, int, int, int, int, int, str]] = []
    for index, build in enumerate(builds):
        if not isinstance(build, dict):
            issues.append(Issue("error", f"build {index + 1} is not an object"))
            continue
        x, y, z = int(build.get("x", center[0])), int(build.get("y", center[1])), int(build.get("z", center[2]))
        w = int(build.get("width", 10)); d = int(build.get("depth", 10)); h = int(build.get("height", 10))
        kind = str(build.get("type", "house"))
        if max(abs(x - center[0]), abs(z - center[2])) > world_radius * 2:
            issues.append(Issue("warning", f"build {index + 1} is far outside the terrain area"))
        if min(w, d, h) < 3:
            issues.append(Issue("error", f"build {index + 1} has an invalid size"))
        if max(w, d, h) > 64:
            issues.append(Issue("error", f"build {index + 1} exceeds the safe size limit"))
        boxes.append((x - w // 2, x + w // 2, z - d // 2, z + d // 2, y, y + h, kind))

    for i, a in enumerate(boxes):
        for j in range(i + 1, len(boxes)):
            b = boxes[j]
            horizontal = a[0] < b[1] and a[1] > b[0] and a[2] < b[3] and a[3] > b[2]
            vertical = a[4] < b[5] and a[5] > b[4]
            if horizontal and vertical:
                issues.append(Issue("warning", f"builds {i + 1} and {j + 1} overlap"))

    for index, road in enumerate(plan.get("roads", [])):
        width = int(road.get("width", 3))
        if width < 1 or width > 5:
            issues.append(Issue("error", f"road {index + 1} has invalid width"))

    if len(builds) > 24:
        issues.append(Issue("error", "plan contains more than 24 major structures"))
    return issues
