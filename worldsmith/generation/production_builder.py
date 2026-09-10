from __future__ import annotations

import math
from typing import Any

from .advanced_builder import AdvancedWorldBuilder
from .terrain_engine import TerrainEngine


_AIR_NAMES = {"minecraft:air", "minecraft:cave_air", "minecraft:void_air", "air", "cave_air", "void_air"}


class _ProtectedLevel:
    """Transparent level proxy that guards every set_version_block call."""

    def __init__(self, target, owner):
        self._target = target
        self._owner = owner

    def set_version_block(self, x, y, z, dimension, version, block, *args, **kwargs):
        return self._owner._guarded_write(x, y, z, dimension, version, block, *args, **kwargs)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._target, name)


class ProductionWorldBuilder(AdvancedWorldBuilder):
    """Production WorldSmith pipeline with global safety, budgeting and improved terrain."""

    def __init__(self, level, dimension: str = "minecraft:overworld", seed: int = 1337):
        super().__init__(level, dimension=dimension, seed=seed)
        self._raw_level = self.level
        self._write_count = 0
        self._skipped_count = 0
        self._existing_chunks: set[tuple[int, int]] = set()
        self._preserve_existing = True
        self._allow_terrain_regeneration = False
        self._max_blocks = 1_500_000
        self._phase = "idle"
        self.level = _ProtectedLevel(self._raw_level, self)

    def _configure_safety(self, plan: dict) -> None:
        safety = plan.get("safety") if isinstance(plan.get("safety"), dict) else {}
        self._preserve_existing = bool(safety.get("preserve_existing", True))
        self._allow_terrain_regeneration = bool(safety.get("allow_terrain_regeneration", False))
        try:
            self._max_blocks = max(100_000, min(int(safety.get("max_blocks", 1_500_000)), 3_000_000))
        except (TypeError, ValueError):
            self._max_blocks = 1_500_000
        try:
            self._existing_chunks = set(self._raw_level.all_chunk_coords(self.dimension))
        except Exception:
            self._existing_chunks = set()
            if self._preserve_existing:
                # Fail closed when we cannot enumerate existing chunks.
                self._allow_terrain_regeneration = False

    @staticmethod
    def _block_name(block) -> str:
        name = getattr(block, "namespaced_name", None)
        if name:
            return str(name)
        namespace = getattr(block, "namespace", None)
        base = getattr(block, "base_name", None)
        if namespace and base:
            return f"{namespace}:{base}"
        return str(block)

    def _guarded_write(self, x, y, z, dimension, version, block, *args, **kwargs) -> bool:
        if self._write_count >= self._max_blocks:
            self._skipped_count += 1
            return False
        x, y, z = int(x), int(y), int(z)
        chunk_pos = (x // 16, z // 16)

        if self._preserve_existing and chunk_pos in self._existing_chunks:
            if self._phase == "terrain" and self._allow_terrain_regeneration:
                pass
            else:
                try:
                    current, _ = self._raw_level.get_version_block(x, y, z, dimension, version)
                    if self._block_name(current) not in _AIR_NAMES:
                        self._skipped_count += 1
                        return False
                except Exception:
                    self._skipped_count += 1
                    return False

        self._raw_level.set_version_block(x, y, z, dimension, version, block, *args, **kwargs)
        self._write_count += 1
        return True

    def _terrain(self) -> TerrainEngine:
        model = getattr(self, "_terrain_model", None)
        if model is None or model.seed != self.seed:
            model = TerrainEngine(self.seed)
            self._terrain_model = model
        return model

    def height_at(self, x: int, z: int, base_y: int, height: int, roughness: float = 1.0) -> int:
        return self._terrain().height(int(x), int(z), int(base_y), int(height), float(roughness))

    @staticmethod
    def _column_blocks(sample, y: int, top: int) -> str:
        if y == top:
            if sample.snow:
                return "minecraft:snow_block"
            if sample.biome == "dryland":
                return "minecraft:sand"
            if sample.wet:
                return "minecraft:moss_block"
            return "minecraft:grass_block"
        if y >= top - 3:
            return "minecraft:sand" if sample.biome == "dryland" else "minecraft:dirt"
        if top - y > 16:
            return "minecraft:stone"
        return "minecraft:stone" if sample.biome in {"alpine_snow", "highland"} else "minecraft:dirt"

    def _tree(self, x: int, y: int, z: int, kind: str = "oak") -> int:
        wood = "minecraft:spruce_log" if kind == "spruce" else "minecraft:oak_log"
        leaves = "minecraft:spruce_leaves" if kind == "spruce" else "minecraft:oak_leaves"
        height = 5 if kind == "spruce" else 4
        changed = 0
        for dy in range(height):
            if self.put(x, y + dy, z, wood):
                changed += 1
        for dy in range(max(1, height - 3), height + 2):
            radius = 1 if dy < height else 2
            for dx in range(-radius, radius + 1):
                for dz in range(-radius, radius + 1):
                    if abs(dx) + abs(dz) <= radius + 1 and self.put(x + dx, y + dy, z + dz, leaves):
                        changed += 1
        return changed

    def generate_terrain(self, cx: int, cz: int, radius: int, base_y: int, mountain_height: int, roughness: float, water: bool = True, vegetation: bool = True) -> tuple[int, int]:
        radius = max(16, min(int(radius), 128))
        mountain_height = max(8, min(int(mountain_height), 128))
        sea_level = base_y + max(3, mountain_height // 9)
        model = self._terrain()
        changed = 0
        columns = 0
        tree_candidates: list[tuple[int, int, int, str]] = []

        for x in range(cx - radius, cx + radius + 1):
            for z in range(cz - radius, cz + radius + 1):
                dx, dz = x - cx, z - cz
                if math.hypot(dx, dz) > radius:
                    continue
                sample = model.sample(dx, dz, base_y, mountain_height, roughness)
                top = sample.height
                if water and sample.river:
                    top = min(top, sea_level - 1)
                for y in range(base_y, top + 1):
                    if self.put(x, y, z, self._column_blocks(sample, y, top)):
                        changed += 1
                if water and top < sea_level:
                    for y in range(top + 1, sea_level + 1):
                        if self.put(x, y, z, "minecraft:water"):
                            changed += 1
                if vegetation and top < base_y + mountain_height * 0.66 and not sample.river:
                    density = model._raw(dx / 2.0, dz / 2.0, mountain_height, roughness)
                    if sample.biome == "wet_forest" and density > 0.68:
                        tree_candidates.append((x, top + 1, z, "oak"))
                    elif sample.biome == "temperate" and density > 0.83:
                        tree_candidates.append((x, top + 1, z, "oak"))
                    elif sample.biome == "highland" and density > 0.90:
                        tree_candidates.append((x, top + 1, z, "spruce"))
                columns += 1

        for x, y, z, kind in tree_candidates[::2][:900]:
            changed += self._tree(x, y, z, kind)
        return changed, columns

    def build(self, plan: dict):
        self._write_count = 0
        self._skipped_count = 0
        self._configure_safety(plan)
        self.seed = int(plan.get("seed", self.seed))
        cx, cy, cz = [int(v) for v in plan.get("center", [0, 100, 0])]
        terrain = plan.get("terrain", {}) if isinstance(plan.get("terrain"), dict) else {}
        radius = int(terrain.get("radius", 96))
        mountain_height = int(terrain.get("mountain_height", 80))
        roughness = float(terrain.get("roughness", 1.0))

        from .builder import BuildResult
        result = BuildResult()

        self._phase = "terrain"
        if terrain.get("enabled", True):
            self.generate_terrain(cx, cz, radius, cy, mountain_height, roughness, bool(terrain.get("water", True)), bool(terrain.get("vegetation", True)))

        self._phase = "caves"
        if terrain.get("caves", True):
            from .caves import CavePass
            CavePass(self.level, self.dimension, self.seed).carve((cx, cy, cz), radius, cy, mountain_height, roughness, self.height_at)

        self._phase = "roads"
        for road in plan.get("roads", [])[:48]:
            self.road(int(road.get("x1", cx)), int(road.get("z1", cz)), int(road.get("x2", cx)), int(road.get("z2", cz)), int(road.get("y", cy + 3)), int(road.get("width", 3)))

        self._phase = "bridges"
        from .bridges import BridgeBuilder
        bridge_builder = BridgeBuilder(self.level, self.dimension)
        for bridge in plan.get("bridges", [])[:16]:
            bridge_builder.build(bridge)

        self._phase = "structures"
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
            result.roads_changed += built.roads_changed
            result.systems_changed += built.systems_changed
            result.structures_changed += built.structures_changed
            result.interiors_changed += built.interiors_changed

        self._phase = "finishing"
        from .decoration import ArchitectureFinisher
        finisher = ArchitectureFinisher(self.level, self.dimension)
        for build in plan.get("builds", [])[:24]:
            report = finisher.finish(build)
            result.interiors_changed += report.interior_blocks

        self._phase = "operations"
        if plan.get("operations"):
            from .primitive_ops import PrimitiveOperationCompiler
            PrimitiveOperationCompiler(self.level, self.dimension).apply(plan["operations"])

        self._phase = "complete"
        result.blocks_changed = self._write_count
        return result

    def redstone_gate(self, x: int, y: int, z: int) -> int:
        report = __import__("worldsmith.generation.redstone", fromlist=["RedstoneEngineer"]).RedstoneEngineer(self.level, self.dimension).gate(x, y, z)
        if not report.valid:
            raise RuntimeError(report.message)
        return report.blocks_changed
