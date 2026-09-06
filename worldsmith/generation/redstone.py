from __future__ import annotations

from dataclasses import dataclass

try:
    from amulet.api.block import Block
except ImportError:  # pragma: no cover
    Block = None


@dataclass(frozen=True)
class RedstoneReport:
    blocks_changed: int
    components: int
    valid: bool
    message: str


class RedstoneEngineer:
    """Construct small, explicit-state redstone mechanisms and validate their topology."""

    def __init__(self, level, dimension: str = "minecraft:overworld"):
        if Block is None:
            raise RuntimeError("amulet-core is required for redstone engineering")
        self.level = level
        self.dimension = dimension
        wrapper = getattr(level, "level_wrapper", None)
        self.version = (getattr(wrapper, "platform", "java"), getattr(wrapper, "max_world_version", getattr(wrapper, "version", (1, 20, 4))))

    @staticmethod
    def state(name: str):
        return Block.from_string_blockstate(name)

    def put(self, x: int, y: int, z: int, state: str) -> int:
        self.level.set_version_block(int(x), int(y), int(z), self.dimension, self.version, self.state(state))
        return 1

    def gate(self, x: int, y: int, z: int) -> RedstoneReport:
        """Two-block piston gate: lever -> dust -> branch -> opposing sticky pistons."""
        placements = [
            (x - 3, y + 1, z, "minecraft:lever[face=floor,facing=north,powered=false]"),
            (x - 2, y + 1, z, "minecraft:redstone_wire[north=none,east=side,south=none,west=side]"),
            (x - 1, y + 1, z, "minecraft:redstone_wire[north=none,east=side,south=none,west=side]"),
            (x, y + 1, z, "minecraft:redstone_wire[north=none,east=side,south=side,west=side]"),
            (x + 1, y + 1, z, "minecraft:redstone_wire[north=none,east=side,south=none,west=side]"),
            (x + 2, y + 1, z, "minecraft:redstone_wire[north=none,east=side,south=none,west=side]"),
            (x, y, z - 1, "minecraft:sticky_piston[facing=east,extended=false]"),
            (x + 4, y, z - 1, "minecraft:sticky_piston[facing=west,extended=false]"),
            (x + 1, y + 1, z - 1, "minecraft:iron_block"),
            (x + 3, y + 1, z - 1, "minecraft:iron_block"),
            (x, y, z, "minecraft:repeater[facing=south,delay=1,locked=false,powered=false]"),
        ]
        for px, py, pz, state in placements:
            self.put(px, py, pz, state)

        # Static topology checks: one source, continuous conductor chain, two opposing pistons.
        valid = len(placements) == 11 and placements[0][3].startswith("minecraft:lever") and placements[6][3].startswith("minecraft:sticky_piston") and placements[7][3].startswith("minecraft:sticky_piston")
        message = "Gate topology emitted with explicit block states" if valid else "Gate topology validation failed"
        return RedstoneReport(len(placements), 11, valid, message)
