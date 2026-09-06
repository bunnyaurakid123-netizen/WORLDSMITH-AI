from __future__ import annotations

from .builder import BuildResult, WorldBuilder
from .decoration import ArchitectureFinisher
from .primitive_ops import PrimitiveOperationCompiler
from .redstone import RedstoneEngineer


class AdvancedWorldBuilder(WorldBuilder):
    """WorldBuilder plus architecture, redstone and validated AI voxel detail passes."""

    def build(self, plan: dict) -> BuildResult:
        result = super().build(plan)

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
