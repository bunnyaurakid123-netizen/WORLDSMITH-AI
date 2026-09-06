import json
import zipfile

from worldsmith.assets.minecraft import AssetSource, MinecraftAssetCatalog


def test_asset_catalog_reads_blockstate_and_model_from_zip(tmp_path):
    archive_path = tmp_path / "pack.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("assets/minecraft/blockstates/stone.json", json.dumps({"variants": {"": {"model": "minecraft:block/stone"}}}))
        archive.writestr("assets/minecraft/models/block/stone.json", json.dumps({"textures": {"all": "minecraft:block/stone"}}))
    source = AssetSource(archive_path, "resource_pack", "test")
    catalog = MinecraftAssetCatalog([source])
    blockstate = catalog.blockstate("minecraft:stone")
    model = catalog.block_model("minecraft:stone")
    assert blockstate["variants"][""]["model"] == "minecraft:block/stone"
    assert "minecraft:block/stone" in catalog.model_texture_ids(model)


def test_identifier_without_namespace_defaults_to_minecraft(tmp_path):
    archive_path = tmp_path / "pack.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("assets/minecraft/blockstates/dirt.json", "{}")
    catalog = MinecraftAssetCatalog([AssetSource(archive_path, "resource_pack", "test")])
    assert catalog.blockstate("dirt") == {}
