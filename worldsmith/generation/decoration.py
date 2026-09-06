from __future__ import annotations

from dataclasses import dataclass

try:
    from amulet.api.block import Block
except ImportError:  # pragma: no cover
    Block = None


@dataclass(frozen=True)
class DecorationReport:
    blocks_changed: int = 0
    interior_blocks: int = 0
    exterior_blocks: int = 0


class ArchitectureFinisher:
    """Second-pass architectural detailer for procedurally generated structures."""

    def __init__(self, level, dimension: str = "minecraft:overworld"):
        if Block is None:
            raise RuntimeError("amulet-core is required for architectural finishing")
        self.level = level
        self.dimension = dimension
        wrapper = getattr(level, "level_wrapper", None)
        self.version = (getattr(wrapper, "platform", "java"), getattr(wrapper, "max_world_version", getattr(wrapper, "version", (1, 20, 4))))
        self._cache: dict[str, Block] = {}

    def blockstate(self, state: str):
        if state not in self._cache:
            self._cache[state] = Block.from_string_blockstate(state)
        return self._cache[state]

    def put(self, x: int, y: int, z: int, state: str) -> int:
        self.level.set_version_block(int(x), int(y), int(z), self.dimension, self.version, self.blockstate(state))
        return 1

    def roof(self, x: int, y: int, z: int, w: int, d: int, h: int, stair_block: str = "minecraft:spruce_stairs") -> int:
        changed = 0
        half = max(2, w // 2)
        roof_y = y + h + 2
        z0, z1 = z - d // 2, z + (d - 1) // 2
        for layer in range(half + 1):
            lx = x - half + layer
            rx = x + half - layer
            level = roof_y + layer
            for zz in range(z0, z1 + 1):
                changed += self.put(lx, level, zz, f"{stair_block}[facing=east,half=bottom,shape=straight,waterlogged=false]")
                if rx != lx:
                    changed += self.put(rx, level, zz, f"{stair_block}[facing=west,half=bottom,shape=straight,waterlogged=false]")
        return changed

    def chimney(self, x: int, y: int, z: int, h: int, block: str = "minecraft:bricks") -> int:
        changed = 0
        top = y + h + 5
        for yy in range(top, top + 5):
            for dx in (-1, 0):
                for dz in (-1, 0):
                    changed += self.put(x + dx, yy, z + dz, block)
        changed += self.put(x, top + 5, z, "minecraft:campfire[lit=true]")
        return changed

    def lanterns(self, x: int, y: int, z: int, w: int, d: int, h: int) -> int:
        changed = 0
        yy = y + max(3, h // 2)
        for px, pz in ((x - w // 2 - 1, z - d // 2 - 1), (x + w // 2 + 1, z - d // 2 - 1), (x - w // 2 - 1, z + d // 2 + 1), (x + w // 2 + 1, z + d // 2 + 1)):
            changed += self.put(px, yy, pz, "minecraft:lantern")
        return changed

    def balcony(self, x: int, y: int, z: int, w: int) -> int:
        changed = 0
        for xx in range(x - w // 2, x + (w + 1) // 2):
            changed += self.put(xx, y, z, "minecraft:spruce_slab[type=bottom,waterlogged=false]")
            changed += self.put(xx, y + 1, z, "minecraft:spruce_fence")
        return changed

    def house_interior(self, x: int, y: int, z: int, w: int, d: int) -> int:
        changed = 0
        room_y = y + 2
        # Bedroom
        changed += self.put(x - max(2, w // 4), room_y, z + max(1, d // 4), "minecraft:white_bed[facing=south,part=foot,occupied=false]")
        changed += self.put(x - max(2, w // 4) - 1, room_y, z + max(1, d // 4), "minecraft:white_bed[facing=south,part=head,occupied=false]")
        # Work corner
        changed += self.put(x + max(2, w // 4), room_y, z - max(1, d // 4), "minecraft:crafting_table")
        changed += self.put(x + max(2, w // 4), room_y, z - max(1, d // 4) + 1, "minecraft:chest")
        # Table and seating
        changed += self.put(x, room_y, z, "minecraft:oak_fence")
        for dx in (-1, 1):
            changed += self.put(x + dx, room_y, z, "minecraft:oak_stairs[facing=" + ("east" if dx < 0 else "west") + ",half=bottom,shape=straight,waterlogged=false]")
        return changed

    def tavern_interior(self, x: int, y: int, z: int, w: int, d: int) -> int:
        changed = 0
        room_y = y + 2
        bar_z = z + d // 4
        for xx in range(x - w // 3, x + w // 3 + 1):
            changed += self.put(xx, room_y, bar_z, "minecraft:dark_oak_slab[type=bottom,waterlogged=false]")
        for xx in range(x - w // 3, x + w // 3 + 1, 2):
            changed += self.put(xx, room_y, bar_z + 2, "minecraft:barrel[facing=up,open=false]")
            changed += self.put(xx, room_y, z - d // 5, "minecraft:oak_stairs[facing=south,half=bottom,shape=straight,waterlogged=false]")
        changed += self.put(x - 2, room_y, z + d // 5, "minecraft:crafting_table")
        changed += self.put(x + 2, room_y, z + d // 5, "minecraft:loom[facing=north]" )
        return changed

    def blacksmith_interior(self, x: int, y: int, z: int, w: int, d: int) -> int:
        changed = 0
        room_y = y + 2
        changed += self.put(x - 2, room_y, z, "minecraft:blast_furnace[facing=east,lit=false]")
        changed += self.put(x, room_y, z, "minecraft:anvil[facing=south]" )
        changed += self.put(x + 2, room_y, z, "minecraft:smithing_table")
        changed += self.put(x + 2, room_y, z + 2, "minecraft:chest")
        changed += self.put(x - 2, room_y, z + 2, "minecraft:grindstone[face=floor,facing=north]" )
        return changed

    def castle_interior(self, x: int, y: int, z: int, w: int, d: int, h: int) -> int:
        changed = 0
        room_y = y + 2
        # Throne dais
        for dx in range(-2, 3):
            changed += self.put(x + dx, room_y, z + d // 4, "minecraft:stone_brick_slab[type=bottom,waterlogged=false]")
        changed += self.put(x, room_y + 1, z + d // 4, "minecraft:dark_oak_stairs[facing=north,half=bottom,shape=straight,waterlogged=false]")
        # Hall lighting
        for dx in (-w // 3, 0, w // 3):
            changed += self.put(x + dx, room_y + 4, z, "minecraft:lantern")
        # Armory wall
        for dz in range(-d // 4, d // 4 + 1, 2):
            changed += self.put(x - w // 3, room_y, z + dz, "minecraft:chest")
        return changed

    def finish(self, build: dict) -> DecorationReport:
        x, y, z = int(build.get("x", 0)), int(build.get("y", 100)), int(build.get("z", 0))
        w = max(7, int(build.get("width", 10))); d = max(7, int(build.get("depth", 10))); h = max(7, int(build.get("height", 10)))
        kind = str(build.get("type", "house")).lower()
        report = DecorationReport()
        exterior = 0; interior = 0

        if kind in {"house", "tavern", "blacksmith", "warehouse", "temple", "tower", "watchtower"}:
            stair = "minecraft:stone_brick_stairs" if kind in {"temple", "tower", "watchtower"} else "minecraft:spruce_stairs"
            exterior += self.roof(x, y, z, w, d, h, stair)
            exterior += self.lanterns(x, y, z, w, d, h)
            if kind in {"house", "tavern"}:
                exterior += self.chimney(x + max(2, w // 4), y, z, h)
                exterior += self.balcony(x, y + h // 2, z + d // 2 + 1, min(w - 2, 7))

        if kind == "house" and build.get("interior", True):
            interior += self.house_interior(x, y, z, w, d)
        elif kind == "tavern" and build.get("interior", True):
            interior += self.tavern_interior(x, y, z, w, d)
        elif kind == "blacksmith" and build.get("interior", True):
            interior += self.blacksmith_interior(x, y, z, w, d)
        elif kind in {"castle", "fortress", "palace", "keep"} and build.get("interior", True):
            interior += self.castle_interior(x, y, z, w, d, h)

        return DecorationReport(exterior + interior, interior, exterior)
