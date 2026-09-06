from __future__ import annotations

from dataclasses import dataclass
import re

from .minecraft import MinecraftAssetCatalog


@dataclass(frozen=True)
class Appearance:
    color: tuple[float, float, float]
    texture_id: str | None = None
    model_id: str | None = None


def normalize_block_id(block) -> str:
    """Convert an Amulet Block or string representation into namespace:name."""
    if hasattr(block, "namespace") and hasattr(block, "base_name"):
        return f"{getattr(block, 'namespace')}:{getattr(block, 'base_name')}"
    if hasattr(block, "base_name"):
        return f"minecraft:{getattr(block, 'base_name')}"
    value = str(block).strip()
    match = re.search(r"([A-Za-z0-9_.-]+:[A-Za-z0-9_./-]+)", value)
    if match:
        return match.group(1)
    return value


class BlockAppearanceCache:
    """Resolve preview colors from vanilla/resource-pack assets using Qt image decoding."""

    def __init__(self, catalog: MinecraftAssetCatalog | None = None):
        self.catalog = catalog or MinecraftAssetCatalog()
        self.cache: dict[str, Appearance] = {}

    @staticmethod
    def _fallback(block_id: str) -> Appearance:
        value = block_id.lower()
        if "snow" in value or "ice" in value:
            color = (0.82, 0.88, 0.96)
        elif "stone" in value or "deepslate" in value or "andesite" in value:
            color = (0.38, 0.40, 0.44)
        elif "sand" in value or "sandstone" in value:
            color = (0.72, 0.61, 0.39)
        elif "water" in value:
            color = (0.10, 0.35, 0.56)
        elif "wood" in value or "log" in value or "plank" in value:
            color = (0.46, 0.29, 0.15)
        elif "grass" in value or "leaves" in value or "moss" in value:
            color = (0.16, 0.40, 0.18)
        else:
            color = (0.32, 0.30, 0.27)
        return Appearance(color)

    def resolve(self, block_id: str) -> Appearance:
        block_id = normalize_block_id(block_id)
        if block_id in self.cache:
            return self.cache[block_id]
        appearance = self._fallback(block_id)
        source = self.catalog.preferred_source()
        blockstate = self.catalog.blockstate(block_id, source)
        model_id = None
        if isinstance(blockstate, dict):
            variants = blockstate.get("variants")
            if isinstance(variants, dict):
                for variant in variants.values():
                    candidate = variant[0] if isinstance(variant, list) and variant else variant
                    if isinstance(candidate, dict) and candidate.get("model"):
                        model_id = str(candidate["model"])
                        break
        if model_id:
            model = self.catalog.block_model(model_id, source)
            if isinstance(model, dict):
                texture_ids = self.catalog.model_texture_ids(model)
                texture_id = next(iter(texture_ids), None)
                if texture_id:
                    try:
                        from PySide6.QtGui import QImage
                        image = QImage.fromData(self.catalog.texture_bytes(texture_id, source) or b"")
                        if not image.isNull():
                            pixel = image.pixelColor(max(0, image.width() // 2), max(0, image.height() // 2))
                            color = (pixel.redF(), pixel.greenF(), pixel.blueF())
                            appearance = Appearance(color, texture_id=texture_id, model_id=model_id)
                    except Exception:
                        appearance = Appearance(appearance.color, texture_id=texture_id, model_id=model_id)
        self.cache[block_id] = appearance
        return appearance
