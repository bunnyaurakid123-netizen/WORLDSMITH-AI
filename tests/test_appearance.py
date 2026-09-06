from worldsmith.assets.appearance import normalize_block_id


def test_normalize_block_object_like_value():
    class FakeBlock:
        namespace = "minecraft"
        base_name = "stone"

    assert normalize_block_id(FakeBlock()) == "minecraft:stone"


def test_normalize_string_value():
    assert normalize_block_id("Block(minecraft:oak_planks)") == "minecraft:oak_planks"
