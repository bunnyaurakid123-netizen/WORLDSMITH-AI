from __future__ import annotations

import math
from dataclasses import dataclass

from worldsmith.generation.noise import fbm, ridge

try:
    from amulet.api.block import Block
except ImportError:  # pragma: no cover
    Block = None


@dataclass
class BuildResult:
    blocks_changed: int = 0
    roads_changed: int = 0
    systems_changed: int = 0
    terrain_columns: int = 0
    structures_changed: int = 0
    interiors_changed: int = 0


class WorldBuilder:
    """Deterministic, bounded Minecraft world-generation engine."""

    def __init__(self, level, dimension: str = "minecraft:overworld", seed: int = 1337):
        if Block is None:
            raise RuntimeError("amulet-core is required for building")
        self.level = level
        self.dimension = dimension
        self.seed = int(seed)
        self._blocks: dict[str, Block] = {}
        wrapper = getattr(level, "level_wrapper", None)
        max_version = getattr(wrapper, "max_world_version", (1, 20, 4))
        self.version = ("java", max_version)

    def block(self, name: str):
        if name not in self._blocks:
            namespace, base = name.split(":", 1)
            self._blocks[name] = Block(namespace, base)
        return self._blocks[name]

    def put(self, x: int, y: int, z: int, name: str) -> bool:
        self.level.set_version_block(
            int(x), int(y), int(z), self.dimension, self.version, self.block(name)
        )
        return True

    @staticmethod
    def _clamp(value: float, low: float, high: float) -> float:
        return max(low, min(high, value))

    def height_at(self, x: int, z: int, base_y: int, height: int, roughness: float = 1.0) -> int:
        macro = fbm(x / 180.0, z / 180.0, self.seed + 11, 5)
        continental = fbm(x / 420.0, z / 420.0, self.seed + 23, 4)
        ridges = ridge(x / 78.0, z / 78.0, self.seed + 37)
        detail = fbm(x / 24.0, z / 24.0, self.seed + 71, 4)
        mask = self._clamp(0.30 + continental * 0.76 + macro * 0.44, 0.0, 1.0)
        alpine = ridges * ridges
        erosion = detail * 0.18
        raw = max(0.0, (mask * 0.42 + alpine * 0.46 + erosion) * roughness)
        return base_y + 2 + int(self._clamp(raw * height, 2, height))

    def _river_distance(self, x: int, z: int, radius: int) -> float:
        p1 = abs(math.sin((z + self.seed * 0.37) / 34.0) * radius * 0.72 - x)
        p2 = abs(math.cos((x - self.seed * 0.23) / 47.0) * radius * 0.55 - z * 0.68)
        p3 = abs(math.sin((x + z) / 86.0) * radius * 0.48 - (x - z) * 0.38)
        return min(p1, p2, p3)

    def _biome_materials(self, x: int, z: int, top: int, base_y: int, peak_height: int):
        climate = fbm(x / 240.0, z / 240.0, self.seed + 101, 4)
        wet = fbm(x / 125.0, z / 125.0, self.seed + 211, 3)
        if top > base_y + peak_height * 0.78:
            return "minecraft:snow_block", "minecraft:stone", "minecraft:spruce_leaves"
        if climate > 0.70 and wet < 0.35:
            return "minecraft:sand", "minecraft:sandstone", "minecraft:dead_bush"
        if wet > 0.68:
            return "minecraft:grass_block", "minecraft:dirt", "minecraft:oak_leaves"
        return "minecraft:grass_block", "minecraft:stone", "minecraft:oak_leaves"

    def generate_terrain(
        self,
        cx: int,
        cz: int,
        radius: int,
        base_y: int,
        mountain_height: int,
        roughness: float,
        water: bool = True,
        vegetation: bool = True,
    ) -> tuple[int, int]:
        changed = 0
        columns = 0
        radius = max(16, min(int(radius), 128))
        mountain_height = max(8, min(int(mountain_height), 120))
        sea_level = base_y + max(2, mountain_height // 10)

        for x in range(cx - radius, cx + radius + 1):
            for z in range(cz - radius, cz + radius + 1):
                dx, dz = x - cx, z - cz
                radial = math.hypot(dx, dz)
                if radial > radius:
                    continue
                falloff = max(0.0, 1.0 - (radial / radius) ** 3)
                h = self.height_at(dx, dz, base_y, mountain_height, roughness)
                h = base_y + 2 + int((h - base_y - 2) * (0.55 + falloff * 0.55))

                river_dist = self._river_distance(dx, dz, radius)
                river_width = 2.8 + mountain_height * 0.035
                near_river = water and river_dist < river_width
                deep_river = river_dist < river_width * 0.40
                if near_river:
                    h = max(base_y + 1, h - int((river_width - river_dist) * 1.9))

                top_block, filler_block, leaf_block = self._biome_materials(
                    dx, dz, h, base_y, mountain_height
                )
                for y in range(base_y, h + 1):
                    if y == h:
                        block = top_block
                    elif y >= h - 3:
                        block = "minecraft:dirt" if "sand" not in top_block else "minecraft:sandstone"
                    else:
                        block = filler_block
                    self.put(x, y, z, block)
                    changed += 1

                if near_river:
                    for y in range(h + 1, sea_level + (1 if deep_river else 0)):
                        if y > h:
                            self.put(x, y, z, "minecraft:water")
                            changed += 1

                if vegetation:
                    slope_x = self.height_at(dx + 2, dz, base_y, mountain_height, roughness)
                    slope_z = self.height_at(dx, dz + 2, base_y, mountain_height, roughness)
                    flat = abs(slope_x - h) <= 2 and abs(slope_z - h) <= 2
                    chance = fbm(dx / 13.0, dz / 13.0, self.seed + 401, 2)
                    if flat and not near_river and h < base_y + mountain_height * 0.68 and chance > 0.86:
                        self.put(x, h + 1, z, "minecraft:grass")
                        if chance > 0.94:
                            self.put(x, h + 2, z, leaf_block)
                        changed += 1
                columns += 1
        return changed, columns

    def foundation(self, x: int, y: int, z: int, w: int, d: int, block: str = "minecraft:stone_bricks") -> int:
        changed = 0
        for xx in range(x - w // 2, x + (w + 1) // 2):
            for zz in range(z - d // 2, z + (d + 1) // 2):
                self.put(xx, y, zz, block)
                changed += 1
        return changed

    def road(self, x1: int, z1: int, x2: int, z2: int, y: int, width: int = 3) -> int:
        changed = 0
        steps = max(abs(x2 - x1), abs(z2 - z1), 1)
        width = max(1, min(width, 5))
        for i in range(steps + 1):
            t = i / steps
            x = round(x1 + (x2 - x1) * t)
            z = round(z1 + (z2 - z1) * t)
            for ox in range(-width // 2, width // 2 + 1):
                for oz in range(-width // 2, width // 2 + 1):
                    self.put(x + ox, y, z + oz, "minecraft:coarse_dirt")
                    changed += 1
        return changed

    def shell(self, x: int, y: int, z: int, w: int, d: int, h: int, wall: str) -> int:
        changed = 0
        x0, x1 = x - w // 2, x + (w - 1) // 2
        z0, z1 = z - d // 2, z + (d - 1) // 2
        for yy in range(y + 1, y + h + 1):
            for xx in range(x0, x1 + 1):
                self.put(xx, yy, z0, wall); self.put(xx, yy, z1, wall); changed += 2
            for zz in range(z0 + 1, z1):
                self.put(x0, yy, zz, wall); self.put(x1, yy, zz, wall); changed += 2
        return changed

    def floor_and_roof(self, x: int, y: int, z: int, w: int, d: int, h: int) -> int:
        changed = 0
        for xx in range(x - w // 2 + 1, x + (w + 1) // 2 - 1):
            for zz in range(z - d // 2 + 1, z + (d + 1) // 2 - 1):
                self.put(xx, y + 1, zz, "minecraft:oak_planks")
                self.put(xx, y + h + 1, zz, "minecraft:spruce_planks")
                changed += 2
        return changed

    def windows_and_door(self, x: int, y: int, z: int, w: int, d: int, h: int) -> int:
        changed = 0
        window_y = y + max(2, h // 2)
        for px, py, pz in (
            (x - w // 2, window_y, z),
            (x + w // 2, window_y, z),
            (x, window_y, z - d // 2),
            (x, window_y, z + d // 2),
        ):
            self.put(px, py, pz, "minecraft:glass_pane")
            changed += 1
        self.put(x, y + 2, z - d // 2, "minecraft:oak_door")
        return changed + 1

    def interior(self, x: int, y: int, z: int, w: int, d: int, h: int, style: str = "house") -> int:
        changed = 0
        inner_w = max(3, w - 4)
        inner_d = max(3, d - 4)
        room_y = y + 2
        for xx in range(x - inner_w // 2, x + (inner_w + 1) // 2, 4):
            for zz in range(z - inner_d // 2, z + (inner_d + 1) // 2, 4):
                self.put(xx, room_y, zz, "minecraft:oak_planks")
                self.put(xx, room_y + max(1, h // 2), zz, "minecraft:lantern")
                changed += 2
        if w >= 10 and d >= 10:
            for dx in (-2, 0, 2):
                self.put(x + dx, room_y, z, "minecraft:oak_planks")
                self.put(x + dx, room_y, z + 1, "minecraft:oak_slab")
                changed += 2
        kind = style.lower()
        if any(token in kind for token in ("tavern", "castle", "palace")):
            for dx in (-max(2, w // 3), max(2, w // 3)):
                self.put(x + dx, room_y, z + max(2, d // 3), "minecraft:chest")
                changed += 1
        if any(token in kind for token in ("house", "village")):
            self.put(x - 2, room_y, z + 2, "minecraft:bed")
            self.put(x + 2, room_y, z + 2, "minecraft:crafting_table")
            changed += 2
        return changed

    def tower(self, x: int, y: int, z: int, r: int, h: int) -> int:
        changed = 0
        r = max(2, r)
        for yy in range(y + 1, y + h + 1):
            for dx in range(-r, r + 1):
                for dz in range(-r, r + 1):
                    dist2 = dx * dx + dz * dz
                    if dist2 <= r * r and dist2 >= max(1, (r - 1) ** 2):
                        self.put(x + dx, yy, z + dz, "minecraft:stone_bricks")
                        changed += 1
        return changed

    def common_build(self, b: dict) -> BuildResult:
        r = BuildResult()
        x, y, z = int(b["x"]), int(b["y"]), int(b["z"])
        w, d, h = int(b["width"]), int(b["depth"]), int(b["height"])
        kind = str(b.get("type", "house")).lower()
        wall = "minecraft:stone_bricks" if kind in {"temple", "blacksmith", "tavern", "warehouse"} else "minecraft:spruce_planks"
        r.blocks_changed += self.foundation(x, y, z, w, d)
        r.blocks_changed += self.shell(x, y, z, w, d, h, wall)
        r.blocks_changed += self.floor_and_roof(x, y, z, w, d, h)
        r.blocks_changed += self.windows_and_door(x, y, z, w, d, h)
        if b.get("interior", True):
            r.interiors_changed += self.interior(x, y, z, w, d, h, kind)
        if kind in {"tower", "watchtower"}:
            r.blocks_changed += self.tower(x, y, z, max(2, w // 4), h + 5)
        if b.get("redstone"):
            r.systems_changed += self.redstone_gate(x, y + 1, z - d // 2 - 1)
        r.structures_changed += 1
        return r

    def castle(self, b: dict) -> BuildResult:
        r = BuildResult()
        x, y, z = int(b["x"]), int(b["y"]), int(b["z"])
        w, d, h = int(b["width"]), int(b["depth"]), int(b["height"])
        r.blocks_changed += self.foundation(x, y, z, w, d)
        r.blocks_changed += self.shell(x, y, z, w, d, h, "minecraft:stone_bricks")
        r.blocks_changed += self.floor_and_roof(x, y, z, w, d, h)
        r.blocks_changed += self.windows_and_door(x, y, z, w, d, h)
        tower_r = max(2, w // 8)
        for tx, tz in (
            (x - w // 2 + 2, z - d // 2 + 2),
            (x + w // 2 - 2, z - d // 2 + 2),
            (x - w // 2 + 2, z + d // 2 - 2),
            (x + w // 2 - 2, z + d // 2 - 2),
        ):
            r.blocks_changed += self.tower(tx, y, tz, tower_r, h + 6)
        r.interiors_changed += self.interior(x, y, z, w, d, h, "castle")
        if b.get("redstone"):
            r.systems_changed += self.redstone_gate(x, y + 1, z - d // 2 - 2)
        r.structures_changed += 1
        return r

    def village(self, b: dict) -> BuildResult:
        r = BuildResult()
        x, y, z = int(b["x"]), int(b["y"]), int(b["z"])
        radius = max(10, min(34, max(int(b["width"]), int(b["depth"])) // 2))
        self.put(x, y, z, "minecraft:stone_bricks")
        for angle_index in range(7):
            angle = angle_index * (math.tau / 7.0)
            dist = radius * (0.58 + 0.16 * fbm(angle_index, 0, self.seed + 991, 2))
            hx = round(x + math.cos(angle) * dist)
            hz = round(z + math.sin(angle) * dist)
            child = {
                "type": "house" if angle_index % 3 else "tavern" if angle_index % 3 == 0 else "blacksmith",
                "x": hx, "y": y, "z": hz,
                "width": 7 + (angle_index % 3) * 2,
                "depth": 7 + ((angle_index + 1) % 3) * 2,
                "height": 7 + (angle_index % 2) * 2,
                "style": b.get("style", "spruce village"),
                "interior": True,
                "redstone": False,
            }
            child_result = self.common_build(child)
            r.blocks_changed += child_result.blocks_changed
            r.interiors_changed += child_result.interiors_changed
            r.systems_changed += child_result.systems_changed
            r.structures_changed += child_result.structures_changed
            r.roads_changed += self.road(x, z, hx, hz, y + 2, 2)
        r.roads_changed += self.road(x - 8, z, x + 8, z, y + 2, 2)
        return r

    def city(self, b: dict) -> BuildResult:
        r = BuildResult()
        x, y, z = int(b["x"]), int(b["y"]), int(b["z"])
        radius = max(16, min(54, max(int(b["width"]), int(b["depth"])) // 2))
        count = 11
        for i in range(count):
            angle = i * math.tau / count
            dist = radius * (0.45 + (i % 3) * 0.16)
            bx = round(x + math.cos(angle) * dist)
            bz = round(z + math.sin(angle) * dist)
            child = {
                "type": "tower" if i % 5 == 0 else "tavern" if i % 4 == 0 else "house",
                "x": bx, "y": y, "z": bz,
                "width": 9 + (i % 4) * 3, "depth": 9 + ((i + 2) % 4) * 2,
                "height": 9 + (i % 3) * 4, "style": b.get("style", "dense medieval city"),
                "interior": True, "redstone": i % 5 == 0,
            }
            cr = self.common_build(child)
            r.blocks_changed += cr.blocks_changed; r.interiors_changed += cr.interiors_changed
            r.systems_changed += cr.systems_changed; r.structures_changed += cr.structures_changed
            r.roads_changed += self.road(x, z, bx, bz, y + 2, 2)
        r.roads_changed += self.road(x - radius, z - radius, x + radius, z - radius, y + 2, 3)
        r.roads_changed += self.road(x - radius, z + radius, x + radius, z + radius, y + 2, 3)
        return r

    def redstone_gate(self, x: int, y: int, z: int) -> int:
        placements = [
            (0, 0, 0, "minecraft:stone_bricks"),
            (1, 0, 0, "minecraft:stone_bricks"),
            (2, 0, 0, "minecraft:redstone_wire"),
            (3, 0, 0, "minecraft:repeater"),
            (4, 0, 0, "minecraft:redstone_wire"),
            (5, 0, 0, "minecraft:sticky_piston"),
            (6, 0, 0, "minecraft:sticky_piston"),
            (2, 1, 0, "minecraft:lever"),
            (5, 1, 0, "minecraft:iron_block"),
            (6, 1, 0, "minecraft:iron_block"),
        ]
        for dx, dy, dz, block in placements:
            self.put(x + dx, y + dy, z + dz, block)
        return len(placements)

    def build(self, plan: dict) -> BuildResult:
        result = BuildResult()
        self.seed = int(plan.get("seed", self.seed))
        cx, cy, cz = [int(v) for v in plan.get("center", [0, 100, 0])]
        terrain = plan.get("terrain", {})
        if terrain.get("enabled", True):
            changed, columns = self.generate_terrain(
                cx, cz,
                int(terrain.get("radius", 96)),
                cy,
                int(terrain.get("mountain_height", 80)),
                float(terrain.get("roughness", 1.0)),
                bool(terrain.get("water", True)),
                bool(terrain.get("vegetation", True)),
            )
            result.blocks_changed += changed
            result.terrain_columns += columns

        for road in plan.get("roads", []):
            result.roads_changed += self.road(
                int(road.get("x1", cx)), int(road.get("z1", cz)),
                int(road.get("x2", cx)), int(road.get("z2", cz)),
                int(road.get("y", cy + 3)), int(road.get("width", 3)),
            )

        for bridge in plan.get("bridges", []):
            result.roads_changed += self.road(
                int(bridge.get("x", cx)), int(bridge.get("z", cz)),
                int(bridge.get("x2", cx + 20)), int(bridge.get("z2", cz)),
                int(bridge.get("y", cy + 4)), int(bridge.get("width", 3)),
            )

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
        return result
