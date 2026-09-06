from __future__ import annotations

from .builder import BuildResult, WorldBuilder
from .decoration import ArchitectureFinisher
from .primitive_ops import PrimitiveOperationCompiler


class AdvancedWorldBuilder(WorldBuilder):
    """WorldBuilder plus architecture finishing and validated AI voxel operations."""

    def build(self, plan: dict) -> BuildResult:
        result = super().build(plan)

        # Finish major top-level structures after the structural pass.
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
