from __future__ import annotations

# Blocks that are normally safe for WorldSmith to replace when creating a requested
# structure or road in an existing natural area. Player-built materials are kept protected.
NATURAL_REPLACEABLE = frozenset({
    "air", "cave_air", "void_air", "stone", "deepslate", "dirt", "coarse_dirt", "rooted_dirt",
    "grass_block", "podzol", "mycelium", "sand", "red_sand", "sandstone", "gravel", "clay",
    "snow", "snow_block", "ice", "packed_ice", "blue_ice", "water", "lava", "moss_block",
    "moss_carpet", "mud", "muddy_mangrove_roots", "powder_snow", "tuff", "calcite", "dripstone_block",
    "pointed_dripstone", "netherrack", "soul_sand", "soul_soil", "basalt", "blackstone", "end_stone",
    "sculk", "sculk_catalyst", "sculk_vein", "oak_log", "spruce_log", "birch_log", "jungle_log",
    "acacia_log", "dark_oak_log", "mangrove_log", "cherry_log", "oak_leaves", "spruce_leaves",
    "birch_leaves", "jungle_leaves", "acacia_leaves", "dark_oak_leaves", "mangrove_leaves", "cherry_leaves",
    "grass", "fern", "large_fern", "dead_bush", "short_grass", "tall_grass", "seagrass", "kelp",
    "kelp_plant", "vine", "glow_lichen", "lily_pad", "dandelion", "poppy", "blue_orchid", "allium",
    "azure_bluet", "red_tulip", "orange_tulip", "white_tulip", "pink_tulip", "oxeye_daisy", "cornflower",
    "lily_of_the_valley", "wither_rose", "sunflower", "lilac", "rose_bush", "peony", "brown_mushroom",
    "red_mushroom", "cactus", "sugar_cane", "sweet_berry_bush", "seagrass", "bamboo", "bamboo_sapling",
})


def short_block_name(block_id: str) -> str:
    value = str(block_id).lower().strip()
    if ":" in value:
        value = value.split(":", 1)[1]
    if "[" in value:
        value = value.split("[", 1)[0]
    return value


def is_air(block_id: str) -> bool:
    return short_block_name(block_id) in {"air", "cave_air", "void_air"}


def is_natural_replaceable(block_id: str) -> bool:
    return short_block_name(block_id) in NATURAL_REPLACEABLE
