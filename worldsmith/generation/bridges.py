from __future__ import annotations

import math
from dataclasses import dataclass

try:
    from amulet.api.block import Block
except ImportError:  # pragma: no cover
    Block = None


@dataclass(frozen=True)
class BridgeReport:
    blocks_changed: int
    supports: int
    deck_blocks: int
    rail_blocks: int


class BridgeBuilder:
    """Construct small, readable bridge structures between two world coordinates."""

    def __init__(self, level, dimension: str = "minecraft:overworld"):
        if Block is None:
            raise RuntimeError("amulet-core is required for bridge generation")
        self.level = level
        self.dimension = dimension
        wrapper = getattr(level, "level_wrapper", None)
        self.version = (getattr(wrapper, "platform", "java"), getattr(wrapper, "max_world_version", getattr(wrapper, "version", (1, 20, 4))))
        self._cache: dict[str, Block] = {}

    def block(self, name: str):
        if name not in self._cache:
            ns, base = name.split(":", 1)
            self._cache[name] = Block(ns, base)
        return self._cache[name]

    def put(self, x: int, y: int, z: int, name: str) -> int:
        self.level.set_version_block(int(x), int(y), int(z), self.dimension, self.version, self.block(name))
        return 1

    def build(self, bridge: dict) -> BridgeReport:
        x1, y, z1 = int(bridge.get("x", 0)), int(bridge.get("y", 100)), int(bridge.get("z", 0))
        x2, z2 = int(bridge.get("x2", x1 + 20)), int(bridge.get("z2", z1))
        width = max(2, min(7, int(bridge.get("width", 3))))
        kind = str(bridge.get("type", "stone_bridge")).lower()

        deck = "minecraft:stone_bricks" if "stone" in kind else "minecraft:dark_oak_planks" if "wood" in kind else "minecraft:deepslate_bricks"
        rail = "minecraft:stone_brick_wall" if "stone" in kind else "minecraft:spruce_fence"
        support = "minecraft:stone_bricks" if "stone" in kind else "minecraft:spruce_log"
        dx, dz = x2 - x1, z2 - z1
        length = max(abs(dx), abs(dz), 1)
        changed = deck_blocks = rail_blocks = supports = 0

        for i in range(length + 1):
            t = i / length
            x = round(x1 + dx * t)
            z = round(z1 + dz * t)
            for lateral in range(-(width // 2), width // 2 + 1):
                # Perpendicular offset keeps bridges aligned even when diagonal.
                px = x + round(-dz / max(1, math.hypot(dx, dz)) * lateral)
                pz = z + round(dx / max(1, math.hypot(dx, dz)) * lateral)
                changed += self.put(px, y, pz, deck); deck_blocks += 1
            if i % 2 == 0:
                left_x = x + round(-dz / max(1, math.hypot(dx, dz)) * (width // 2 + 1))
                left_z = z + round(dx / max(1, math.hypot(dx, dz)) * (width // 2 + 1))
                right_x = x - round(-dz / max(1, math.hypot(dx, dz)) * (width // 2 + 1))
                right_z = z - round(dx / max(1, math.hypot(dx, dz)) * (width // 2 + 1))
                changed += self.put(left_x, y + 1, left_z, rail); changed += self.put(right_x, y + 1, right_z, rail)
                rail_blocks += 2

            if i in (0, length) or i % 6 == 0:
                column_height = max(3, min(10, y + 1))
                for py in range(y - 1, max(-64, y - column_height), -1):
                    changed += self.put(x, py, z, support)
                supports += 1

        return BridgeReport(changed, supports, deck_blocks, rail_blocks)
