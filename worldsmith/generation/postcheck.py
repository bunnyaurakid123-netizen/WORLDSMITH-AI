from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class VerificationIssue:
    severity: str
    message: str


@dataclass(frozen=True)
class VerificationReport:
    checked_structures: int
    checked_roads: int
    issues: tuple[VerificationIssue, ...]

    @property
    def passed(self) -> bool:
        return not any(issue.severity == "error" for issue in self.issues)


class PostBuildVerifier:
    """Lightweight factual verification of the blocks written by a plan."""

    def __init__(self, level, dimension: str = "minecraft:overworld"):
        self.level = level
        self.dimension = dimension
        wrapper = getattr(level, "level_wrapper", None)
        self.version = (getattr(wrapper, "platform", "java"), getattr(wrapper, "max_world_version", getattr(wrapper, "version", (1, 20, 4))))

    @staticmethod
    def _is_air(block) -> bool:
        text = str(block).lower()
        return "air" in text or text.endswith(":void")

    def occupied(self, x: int, y: int, z: int) -> bool:
        try:
            block, _ = self.level.get_version_block(int(x), int(y), int(z), self.dimension, self.version)
            return not self._is_air(block)
        except Exception:
            return False

    def verify(self, plan: dict) -> VerificationReport:
        issues: list[VerificationIssue] = []
        structures = [b for b in plan.get("builds", [])[:24] if isinstance(b, dict)]
        roads = [r for r in plan.get("roads", [])[:48] if isinstance(r, dict)]
        checked_structures = 0
        checked_roads = 0

        for index, build in enumerate(structures, 1):
            x = int(build.get("x", 0)); y = int(build.get("y", 100)); z = int(build.get("z", 0))
            w = max(5, int(build.get("width", 10))); d = max(5, int(build.get("depth", 10))); h = max(5, int(build.get("height", 10)))
            samples = [
                (x, y + 1, z),
                (x - w // 2, y + 1, z),
                (x + w // 2, y + 1, z),
                (x, y + h, z),
            ]
            occupied = sum(self.occupied(*point) for point in samples)
            checked_structures += 1
            if occupied < 2:
                issues.append(VerificationIssue("error", f"Structure {index} appears mostly empty at its expected coordinates"))

        for index, road in enumerate(roads, 1):
            p1 = (int(road.get("x1", 0)), int(road.get("y", 100)), int(road.get("z1", 0)))
            p2 = (int(road.get("x2", 0)), int(road.get("y", 100)), int(road.get("z2", 0)))
            checked_roads += 1
            if not (self.occupied(*p1) or self.occupied(*p2)):
                issues.append(VerificationIssue("warning", f"Road {index} has no occupied endpoint at its planned Y"))

        return VerificationReport(checked_structures, checked_roads, tuple(issues))
