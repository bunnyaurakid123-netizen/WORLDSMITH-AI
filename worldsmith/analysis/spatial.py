from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SpatialSnapshot:
    center: tuple[int, int, int]
    radius: int
    samples: int
    min_height: int
    max_height: int
    mean_height: float
    occupied_ratio: float
    water_ratio: float
    vegetation_ratio: float
    material_families: dict[str, int]

    def text(self) -> str:
        families = ", ".join(f"{name}={count}" for name, count in sorted(self.material_families.items()))
        return (
            f"Spatial analysis center={self.center} radius={self.radius} samples={self.samples}\n"
            f"Height min={self.min_height} max={self.max_height} mean={self.mean_height:.1f}\n"
            f"Occupied={self.occupied_ratio:.1%} water={self.water_ratio:.1%} vegetation={self.vegetation_ratio:.1%}\n"
            f"Material families: {families or 'none'}"
        )


def _family(block_id: str) -> str:
    value = block_id.lower()
    for token, name in (
        ("stone", "stone"), ("deepslate", "deepslate"), ("dirt", "soil"),
        ("grass", "grass"), ("sand", "sand"), ("water", "water"),
        ("lava", "lava"), ("wood", "wood"), ("log", "wood"),
        ("leaves", "vegetation"), ("flower", "vegetation"), ("fern", "vegetation"),
        ("glass", "glass"), ("brick", "brick"), ("quartz", "quartz"),
    ):
        if token in value:
            return name
    return "other"


def _is_air(block) -> bool:
    value = str(block).lower()
    return "air" in value or value.endswith(":void")


def analyze_level(level, center: tuple[int, int, int], radius: int = 32, step: int = 4) -> SpatialSnapshot:
    radius = max(8, min(int(radius), 64))
    step = max(2, min(int(step), 8))
    cx, cy, cz = [int(v) for v in center]
    wrapper = getattr(level, "level_wrapper", None)
    version = getattr(wrapper, "max_world_version", getattr(wrapper, "version", (1, 20, 4)))
    platform = getattr(wrapper, "platform", "java")
    version_key = (platform, version)

    heights: list[int] = []
    occupied = water = vegetation = 0
    families: Counter[str] = Counter()

    for x in range(cx - radius, cx + radius + 1, step):
        for z in range(cz - radius, cz + radius + 1, step):
            top = -64
            top_block = "minecraft:air"
            for y in range(320, -65, -4):
                block, _ = level.get_version_block(x, y, z, "minecraft:overworld", version_key)
                if not _is_air(block):
                    top = y
                    top_block = str(block)
                    break
            heights.append(top)
            if not _is_air(top_block):
                occupied += 1
            family = _family(top_block)
            families[family] += 1
            if family == "water":
                water += 1
            if family == "vegetation":
                vegetation += 1

    samples = max(1, len(heights))
    return SpatialSnapshot(
        center=(cx, cy, cz), radius=radius, samples=len(heights),
        min_height=min(heights), max_height=max(heights), mean_height=sum(heights) / samples,
        occupied_ratio=occupied / samples, water_ratio=water / samples, vegetation_ratio=vegetation / samples,
        material_families=dict(families),
    )


def analyze_save(path: Path, center: tuple[int, int, int], radius: int = 32) -> SpatialSnapshot | None:
    try:
        import amulet
        level = amulet.load_level(str(path))
    except Exception:
        return None
    try:
        return analyze_level(level, center, radius)
    finally:
        try:
            level.close()
        except Exception:
            pass
