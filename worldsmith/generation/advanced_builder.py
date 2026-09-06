from __future__ import annotations

from .builder import BuildResult, WorldBuilder
from .primitive_ops import PrimitiveOperationCompiler


class AdvancedWorldBuilder(WorldBuilder):
    """WorldBuilder plus validated AI-authored primitive voxel operations."""

    def build(self, plan: dict) -> BuildResult:
        result = super().build(plan)
        operations = plan.get("operations", [])
        if operations:
            report = PrimitiveOperationCompiler(self.level, self.dimension).apply(operations)
            result.blocks_changed += report.blocks_changed
        return result
