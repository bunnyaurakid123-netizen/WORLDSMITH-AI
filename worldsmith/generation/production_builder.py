from __future__ import annotations

import math

from .advanced_builder import AdvancedWorldBuilder
from .terrain_engine import TerrainEngine


class ProductionWorldBuilder(AdvancedWorldBuilder):
    """WorldSmith production builder: improved terrain, rivers, biome materials and trees."""

    def _terrain(self) -> TerrainEngine:
        model = getattr(self, "_terrain_model", None)
        if model is None or model.seed != self.seed:
            model = TerrainEngine(self.seed)
            self._terrain_model = model
        return model

    def height_at(self, x: int, z: int, base_y: int, height: int, roughness: float = 1.0) -> int:
        return self._terrain().height(int(x), int(z), int(base_y), int(height), float(roughness))

    @staticmethod
    def _column_blocks(sample, y: int, top: int, base_y: int) -> str:
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
            self.put(x, y + dy, z, wood)
            changed += 1
        for dy in range(max(1, height - 3), height + 2):
            radius = 1 if dy < height else 2
            for dx in range(-radius, radius + 1):
                for dz in range(-radius, radius + 1):
                    if abs(dx) + abs(dz) <= radius + 1:
                        self.put(x + dx, y + dy, z + dz, leaves)
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
                    self.put(x, y, z, self._column_blocks(sample, y, top, base_y))
                    changed += 1
                if water and top < sea_level:
                    for y in range(top + 1, sea_level + 1):
                        self.put(x, y, z, "minecraft:water")
                        changed += 1
                if vegetation and top < base_y + mountain_height * 0.66 and not sample.river:
                    # Deterministic density test; trees are emitted after terrain so their roots are stable.
                    density = model._raw(dx / 2.0, dz / 2.0, mountain_height, roughness)
                    if sample.biome == "wet_forest" and density > 0.68:
                        tree_candidates.append((x, top + 1, z, "oak"))
                    elif sample.biome == "temperate" and density > 0.83:
                        tree_candidates.append((x, top + 1, z, "oak"))
                    elif sample.biome == "highland" and density > 0.90:
                        tree_candidates.append((x, top + 1, z, "spruce"))
                columns += 1

        # Keep foliage bounded so tree detail cannot dominate large terrain builds.
        for x, y, z, kind in tree_candidates[::2][:900]:
            changed += self._tree(x, y, z, kind)
        return changed, columns
