from __future__ import annotations

import math
import random
from dataclasses import dataclass

from worldsmith.generation.noise import fbm

try:
    from amulet.api.block import Block
except ImportError:  # pragma: no cover
    Block = None


@dataclass(frozen=True)
class LandscapeReport:
    blocks_changed: int
    trees: int
    boulders: int
    details: int


class LandscapingPass:
    """Seeded environmental detail pass that follows the generated terrain profile."""

    def __init__(self, level, dimension: str = "minecraft:overworld", seed: int = 1337):
        if Block is None:
            raise RuntimeError("amulet-core is required for landscaping")
        self.level = level
        self.dimension = dimension
        self.seed = int(seed)
        wrapper = getattr(level, "level_wrapper", None)
        self.version = (getattr(wrapper, "platform", "java"), getattr(wrapper, "max_world_version", getattr(wrapper, "version", (1, 20, 4))))
        self._cache: dict[str, Block] = {}

    def block(self, name: str):
        if name not in self._cache:
            namespace, base = name.split(":", 1)
            self._cache[name] = Block(namespace, base)
        return self._cache[name]

    def put(self, x: int, y: int, z: int, block: str) -> int:
        self.level.set_version_block(int(x), int(y), int(z), self.dimension, self.version, self.block(block))
        return 1

    def _height(self, x: int, z: int, base_y: int, mountain_height: int, roughness: float) -> int:
        macro = fbm(x / 180.0, z / 180.0, self.seed + 11, 5)
        continent = fbm(x / 420.0, z / 420.0, self.seed + 23, 4)
        ridge = fbm(x / 78.0, z / 78.0, self.seed + 37, 5)
        detail = fbm(x / 24.0, z / 24.0, self.seed + 71, 4)
        raw = max(0.0, (0.30 + continent * 0.76 + macro * 0.44) * 0.42 + (1.0 - abs(ridge * 2 - 1)) ** 2 * 0.46 + detail * 0.18)
        return base_y + 2 + int(max(2.0, min(float(mountain_height), raw * mountain_height)) * roughness)

    def tree(self, x: int, y: int, z: int, kind: str = "oak", scale: int = 1) -> int:
        changed = 0
        trunk = "minecraft:spruce_log" if kind == "spruce" else "minecraft:oak_log"
        leaves = "minecraft:spruce_leaves" if kind == "spruce" else "minecraft:oak_leaves"
        height = 4 + scale
        for yy in range(y, y + height):
            changed += self.put(x, yy, z, trunk)
        top = y + height
        for dy in range(-2, 3):
            radius = 2 if abs(dy) < 2 else 1
            for dx in range(-radius, radius + 1):
                for dz in range(-radius, radius + 1):
                    if dx * dx + dz * dz <= radius * radius + 1 and not (abs(dx) == radius and abs(dz) == radius):
                        changed += self.put(x + dx, top + dy, z + dz, leaves)
        return changed

    def boulder(self, x: int, y: int, z: int, radius: int = 2) -> int:
        changed = 0
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                for dz in range(-radius, radius + 1):
                    if dx * dx + dy * dy + dz * dz <= radius * radius:
                        changed += self.put(x + dx, y + dy, z + dz, "minecraft:stone")
        return changed

    def shrubs(self, x: int, y: int, z: int) -> int:
        changed = 0
        changed += self.put(x, y, z, "minecraft:oak_leaves")
        if (x + z + self.seed) % 3 == 0:
            changed += self.put(x + 1, y, z, "minecraft:fern")
        return changed

    def landmark(self, x: int, y: int, z: int, style: str) -> int:
        changed = 0
        if style == "obelisk":
            for yy in range(y, y + 7):
                changed += self.put(x, yy, z, "minecraft:stone_bricks")
            changed += self.put(x, y + 7, z, "minecraft:glowstone")
        elif style == "ruin":
            for dx, dz, h in [(-3, -2, 4), (3, 1, 3), (-1, 3, 2)]:
                for yy in range(y, y + h):
                    changed += self.put(x + dx, yy, z + dz, "minecraft:mossy_stone_bricks")
        else:
            changed += self.put(x, y, z, "minecraft:moss_block")
        return changed

    def apply(self, center: tuple[int, int, int], radius: int, base_y: int, mountain_height: int, roughness: float, style: str = "natural") -> LandscapeReport:
        cx, _, cz = center
        radius = max(16, min(int(radius), 128))
        rng = random.Random(self.seed + 8121)
        changed = trees = boulders = details = 0
        stride = 6

        for x in range(cx - radius + 3, cx + radius - 2, stride):
            for z in range(cz - radius + 3, cz + radius - 2, stride):
                dx, dz = x - cx, z - cz
                if math.hypot(dx, dz) > radius - 3:
                    continue
                h = self._height(dx, dz, base_y, mountain_height, roughness)
                flat_x = self._height(dx + 2, dz, base_y, mountain_height, roughness)
                flat_z = self._height(dx, dz + 2, base_y, mountain_height, roughness)
                flat = abs(flat_x - h) <= 2 and abs(flat_z - h) <= 2
                climate = fbm(dx / 240.0, dz / 240.0, self.seed + 101, 4)
                wet = fbm(dx / 125.0, dz / 125.0, self.seed + 211, 3)
                chance = fbm(dx / 18.0, dz / 18.0, self.seed + 404, 3)

                if flat and h < base_y + mountain_height * 0.62 and chance > 0.63:
                    if climate < 0.72 and wet < 0.75:
                        kind = "spruce" if h > base_y + mountain_height * 0.42 else "oak"
                        size = 1 if rng.random() < 0.82 else 2
                        changed += self.tree(x, h + 1, z, kind, size)
                        trees += 1
                elif chance > 0.78 and h > base_y + mountain_height * 0.55:
                    radius_boulder = 1 if rng.random() < 0.75 else 2
                    changed += self.boulder(x, h + 1, z, radius_boulder)
                    boulders += 1
                elif flat and chance > 0.55:
                    changed += self.shrubs(x, h + 1, z)
                    details += 1

        # Sparse landmarks near the perimeter give players recognizable navigation points.
        for angle in (0.55, 2.3, 4.2, 5.5):
            lx = int(cx + math.cos(angle) * radius * 0.78)
            lz = int(cz + math.sin(angle) * radius * 0.78)
            ly = self._height(lx - cx, lz - cz, base_y, mountain_height, roughness)
            landmark_style = "obelisk" if style == "fantasy" else "ruin"
            changed += self.landmark(lx, ly + 1, lz, landmark_style)
            details += 1

        return LandscapeReport(changed, trees, boulders, details)
