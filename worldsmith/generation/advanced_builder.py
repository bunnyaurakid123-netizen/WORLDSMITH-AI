from __future__ import annotations

from .builder import BuildResult, WorldBuilder
from .decoration import ArchitectureFinisher
from .landscape import LandscapingPass
from .primitive_ops import PrimitiveOperationCompiler
from .redstone import RedstoneEngineer


class AdvancedWorldBuilder(WorldBuilder):
    """WorldBuilder plus architecture, landscaping, redstone and AI voxel detail passes."""

    def build(self, plan: dict) -> BuildResult:
        result = super().build(plan)
        cx, cy, cz = [int(v) for v in plan.get("center", [0, 100, 0])]
        terrain = plan.get("terrain", {})

        landscape = LandscapingPass(self.level, self.dimension, int(plan.get("seed", self.seed))).apply(
            (cx, cy, cz),
            int(terrain.get("radius", 96)),
            cy,
            int(terrain.get("mountain_height", 80)),
            float(terrain.get("roughness", 1.0)),
            str(plan.get("style", "natural")).lower(),
        )
        result.blocks_changed += landscape.blocks_changed

        finisher = ArchitectureFinisher(self.level, self.dimension)
        for build in plan.get("builds", [])[:24]:
            report = finisher.finish(build)
            result.blocks_changed += report.blocks_changed
            result.interiors_changed += report.interior_blocks

        operations = plan.get("operations", [])
        if operations:
            report = PrimitiveOperationCompiler(self.level, self.dimension).apply(operations)
            result.blocks_changed += report.blocks_changed

        return result

    def redstone_gate(self, x: int, y: int, z: int) -> int:
        report = RedstoneEngineer(self.level, self.dimension).gate(x, y, z)
        if not report.valid:
            raise RuntimeError(report.message)
        return report.blocks_changed
