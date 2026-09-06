from __future__ import annotations

from .bridges import BridgeBuilder
from .builder import BuildResult, WorldBuilder
from .caves import CavePass
from .decoration import ArchitectureFinisher
from .landscape import LandscapingPass
from .primitive_ops import PrimitiveOperationCompiler
from .redstone import RedstoneEngineer


class AdvancedWorldBuilder(WorldBuilder):
    """AAA generation pipeline with deliberate terrain -> detail -> infrastructure -> structures ordering."""

    def build(self, plan: dict) -> BuildResult:
        result = BuildResult()
        cx, cy, cz = [int(v) for v in plan.get("center", [0, 100, 0])]
        terrain = plan.get("terrain", {})
        seed = int(plan.get("seed", self.seed))
        radius = int(terrain.get("radius", 96))
        mountain_height = int(terrain.get("mountain_height", 80))
        roughness = float(terrain.get("roughness", 1.0))
        self.seed = seed

        # 1. Base terrain first.
        if terrain.get("enabled", True):
            changed, columns = self.generate_terrain(
                cx,
                cz,
                radius,
                cy,
                mountain_height,
                roughness,
                bool(terrain.get("water", True)),
                False,
            )
            result.blocks_changed += changed
            result.terrain_columns += columns

        # 2. Carve underground features into terrain before anything is built above them.
        if terrain.get("caves", True):
            caves = CavePass(self.level, self.dimension, seed).carve(
                (cx, cy, cz), radius, cy, mountain_height, roughness, self.height_at
            )
            result.blocks_changed += caves.blocks_changed

        # 3. Environmental detail. Structures later overwrite any incidental foliage in their footprints.
        if terrain.get("vegetation", True):
            landscape = LandscapingPass(
                self.level, self.dimension, seed
            ).apply(
                (cx, cy, cz), radius, cy, mountain_height, roughness,
                str(plan.get("style", "natural")).lower(),
            )
            result.blocks_changed += landscape.blocks_changed

        # 4. Roads and purpose-built bridges before architecture.
        for road in plan.get("roads", [])[:48]:
            result.roads_changed += self.road(
                int(road.get("x1", cx)),
                int(road.get("z1", cz)),
                int(road.get("x2", cx)),
                int(road.get("z2", cz)),
                int(road.get("y", cy + 3)),
                int(road.get("width", 3)),
            )

        bridge_builder = BridgeBuilder(self.level, self.dimension)
        for bridge in plan.get("bridges", [])[:16]:
            report = bridge_builder.build(bridge)
            result.blocks_changed += report.blocks_changed
            result.roads_changed += report.deck_blocks

        # 5. Major structures.
        for build in plan.get("builds", [])[:24]:
            kind = str(build.get("type", "house")).lower()
            if kind in {"castle", "fortress", "palace", "keep"}:
                built = self.castle(build)
            elif kind in {"village", "settlement"}:
                built = self.village(build)
            elif kind in {"city", "town"}:
                built = self.city(build)
            else:
                built = self.common_build(build)
            result.blocks_changed += built.blocks_changed
            result.roads_changed += built.roads_changed
            result.systems_changed += built.systems_changed
            result.structures_changed += built.structures_changed
            result.interiors_changed += built.interiors_changed

        # 6. Architecture finishing pass after shells exist.
        finisher = ArchitectureFinisher(self.level, self.dimension)
        for build in plan.get("builds", [])[:24]:
            report = finisher.finish(build)
            result.blocks_changed += report.blocks_changed
            result.interiors_changed += report.interior_blocks

        # 7. AI-authored fine-grained voxel details last.
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
