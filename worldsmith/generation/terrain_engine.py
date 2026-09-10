from __future__ import annotations

import math
from dataclasses import dataclass

from .noise import fbm, ridge


@dataclass(frozen=True)
class TerrainSample:
    height: int
    biome: str
    river: bool
    snow: bool
    wet: bool


class TerrainEngine:
    """Deterministic terrain model with domain warp, erosion smoothing and river masks."""

    def __init__(self, seed: int):
        self.seed = int(seed)
        self._cache: dict[tuple[int, int, int, int, float], TerrainSample] = {}

    def _raw(self, x: float, z: float, mountain_height: int, roughness: float) -> float:
        sx = fbm(x / 260.0, z / 260.0, self.seed + 1001, 4)
        sz = fbm(x / 260.0, z / 260.0, self.seed + 2003, 4)
        wx = x + (sx - 0.5) * 72.0
        wz = z + (sz - 0.5) * 72.0
        continental = fbm(wx / 520.0, wz / 520.0, self.seed + 17, 5)
        macro = fbm(wx / 180.0, wz / 180.0, self.seed + 29, 5)
        alpine = ridge(wx / 86.0, wz / 86.0, self.seed + 41)
        detail = fbm(wx / 31.0, wz / 31.0, self.seed + 53, 4)
        erosion = fbm(wx / 115.0, wz / 115.0, self.seed + 67, 3)
        continental = max(0.0, min(1.0, continental * 0.70 + macro * 0.30))
        alpine = alpine * alpine
        value = continental * 0.34 + alpine * 0.51 + detail * 0.15
        # Erosion suppresses steep micro-noise while preserving major ridges.
        value *= 0.90 + erosion * 0.16
        return max(0.0, min(1.0, value * max(0.35, min(1.75, roughness))))

    def sample(self, x: int, z: int, base_y: int, mountain_height: int, roughness: float) -> TerrainSample:
        key = (int(x), int(z), int(base_y), int(mountain_height), round(float(roughness), 3))
        if key in self._cache:
            return self._cache[key]

        raw = self._raw(x, z, mountain_height, roughness)
        neighbor_mean = sum(
            self._raw(x + dx * 5, z + dz * 5, mountain_height, roughness)
            for dx, dz in ((-1, 0), (1, 0), (0, -1), (0, 1))
        ) / 4.0
        smooth = raw * 0.72 + neighbor_mean * 0.28

        river_noise = abs(fbm(x / 135.0, z / 135.0, self.seed + 701, 4) - 0.5)
        river = river_noise < 0.035 and smooth < 0.80
        if river:
            smooth *= 0.57 + river_noise / 0.07

        height = base_y + 3 + int(max(0.0, min(1.0, smooth)) * mountain_height)
        temperature = fbm(x / 340.0, z / 340.0, self.seed + 809, 3)
        moisture = fbm(x / 175.0, z / 175.0, self.seed + 907, 3)
        snow = smooth > 0.74 or (temperature < 0.28 and smooth > 0.55)
        wet = river or moisture > 0.64
        if snow:
            biome = "alpine_snow"
        elif temperature > 0.72 and moisture < 0.34:
            biome = "dryland"
        elif moisture > 0.72:
            biome = "wet_forest"
        elif smooth > 0.62:
            biome = "highland"
        else:
            biome = "temperate"
        result = TerrainSample(height, biome, river, snow, wet)
        self._cache[key] = result
        return result

    def height(self, x: int, z: int, base_y: int, mountain_height: int, roughness: float) -> int:
        return self.sample(x, z, base_y, mountain_height, roughness).height
