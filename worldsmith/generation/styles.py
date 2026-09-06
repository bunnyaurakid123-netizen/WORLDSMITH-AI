from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StylePalette:
    wall: str
    foundation: str
    floor: str
    roof: str
    stair: str
    glass: str
    door: str
    trim: str
    light: str
    fence: str


PALETTES = {
    "medieval": StylePalette("minecraft:stone_bricks", "minecraft:stone", "minecraft:oak_planks", "minecraft:spruce_planks", "minecraft:spruce_stairs", "minecraft:glass_pane", "minecraft:oak_door", "minecraft:spruce_planks", "minecraft:lantern", "minecraft:spruce_fence"),
    "fantasy": StylePalette("minecraft:deepslate_bricks", "minecraft:polished_deepslate", "minecraft:dark_oak_planks", "minecraft:dark_oak_planks", "minecraft:dark_oak_stairs", "minecraft:tinted_glass", "minecraft:dark_oak_door", "minecraft:amethyst_block", "minecraft:soul_lantern", "minecraft:dark_oak_fence"),
    "nordic": StylePalette("minecraft:stone_bricks", "minecraft:cobblestone", "minecraft:spruce_planks", "minecraft:spruce_planks", "minecraft:spruce_stairs", "minecraft:glass_pane", "minecraft:spruce_door", "minecraft:stripped_spruce_log", "minecraft:lantern", "minecraft:spruce_fence"),
    "rustic": StylePalette("minecraft:cobblestone", "minecraft:stone", "minecraft:oak_planks", "minecraft:spruce_planks", "minecraft:spruce_stairs", "minecraft:glass_pane", "minecraft:oak_door", "minecraft:oak_log", "minecraft:lantern", "minecraft:oak_fence"),
    "desert": StylePalette("minecraft:sandstone", "minecraft:smooth_sandstone", "minecraft:smooth_sandstone", "minecraft:sandstone", "minecraft:sandstone_stairs", "minecraft:glass_pane", "minecraft:acacia_door", "minecraft:cut_sandstone", "minecraft:lantern", "minecraft:acacia_fence"),
    "industrial": StylePalette("minecraft:deepslate_bricks", "minecraft:deepslate", "minecraft:polished_deepslate", "minecraft:copper_block", "minecraft:cut_copper_stairs", "minecraft:tinted_glass", "minecraft:iron_door", "minecraft:iron_block", "minecraft:lantern", "minecraft:iron_bars"),
    "modern": StylePalette("minecraft:quartz_block", "minecraft:polished_andesite", "minecraft:quartz_block", "minecraft:polished_blackstone", "minecraft:polished_blackstone_stairs", "minecraft:glass", "minecraft:iron_door", "minecraft:blackstone", "minecraft:sea_lantern", "minecraft:iron_bars"),
    "elven": StylePalette("minecraft:mossy_stone_bricks", "minecraft:moss_block", "minecraft:birch_planks", "minecraft:birch_planks", "minecraft:birch_stairs", "minecraft:glass_pane", "minecraft:birch_door", "minecraft:birch_log", "minecraft:lantern", "minecraft:birch_fence"),
    "volcanic": StylePalette("minecraft:blackstone", "minecraft:polished_blackstone", "minecraft:dark_oak_planks", "minecraft:blackstone", "minecraft:blackstone_stairs", "minecraft:tinted_glass", "minecraft:dark_oak_door", "minecraft:polished_blackstone", "minecraft:soul_lantern", "minecraft:nether_brick_fence"),
}


def resolve_style(style: str | None) -> StylePalette:
    value = str(style or "medieval").lower()
    for keyword, palette in PALETTES.items():
        if keyword in value:
            return palette
    return PALETTES["medieval"]
