from __future__ import annotations

from .transactions import BlockState


class AmuletAdapter:
    """Small version-aware adapter around an open Amulet world."""

    def __init__(self, level, dimension: str = "minecraft:overworld"):
        self.level = level
        self.dimension = dimension
        wrapper = getattr(level, "level_wrapper", None)
        platform = getattr(wrapper, "platform", "java")
        version = getattr(wrapper, "max_world_version", getattr(wrapper, "version", (1, 20, 4)))
        self.version = (platform, version)

    def get_block(self, x: int, y: int, z: int) -> BlockState:
        block, entity = self.level.get_version_block(int(x), int(y), int(z), self.dimension, self.version)
        return BlockState(block, entity)

    def set_block(self, x: int, y: int, z: int, state: BlockState) -> None:
        self.level.set_version_block(
            int(x), int(y), int(z), self.dimension, self.version, state.block, state.entity
        )


class Palette:
    """Validated Minecraft block palette for common editor operations."""

    COMMON = {
        "air": "minecraft:air",
        "stone": "minecraft:stone",
        "cobblestone": "minecraft:cobblestone",
        "stone_bricks": "minecraft:stone_bricks",
        "deepslate": "minecraft:deepslate",
        "grass": "minecraft:grass_block",
        "dirt": "minecraft:dirt",
        "coarse_dirt": "minecraft:coarse_dirt",
        "sand": "minecraft:sand",
        "gravel": "minecraft:gravel",
        "snow": "minecraft:snow_block",
        "oak": "minecraft:oak_planks",
        "spruce": "minecraft:spruce_planks",
        "dark_oak": "minecraft:dark_oak_planks",
        "birch": "minecraft:birch_planks",
        "glass": "minecraft:glass",
        "bricks": "minecraft:bricks",
        "quartz": "minecraft:quartz_block",
        "iron": "minecraft:iron_block",
        "gold": "minecraft:gold_block",
        "copper": "minecraft:copper_block",
        "water": "minecraft:water",
        "lava": "minecraft:lava",
        "glowstone": "minecraft:glowstone",
    }

    @classmethod
    def resolve(cls, value: str) -> str:
        value = str(value).strip().lower()
        if value in cls.COMMON:
            return cls.COMMON[value]
        if ":" in value and all(part and " " not in part for part in value.split(":", 1)):
            return value
        raise ValueError(f"Unsupported block identifier: {value!r}")
