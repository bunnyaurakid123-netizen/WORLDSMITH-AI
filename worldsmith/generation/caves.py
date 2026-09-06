from __future__ import annotations

import math
from dataclasses import dataclass

from worldsmith.generation.noise import fbm

try:
    from amulet.api.block import Block
except ImportError:  # pragma: no cover
    Block = None


@dataclass(frozen=True)
class CaveReport:
    blocks_changed: int
    tunnels: int
    caverns: int


def _hash3(x: int, y: int, z: int, seed: int) -> float:
    n = (x * 374761393 + y * 668265263 + z * 2147483647 + seed * 1442695041) & 0xFFFFFFFF
    n = (n ^ (n >> 13)) * 1274126177 & 0xFFFFFFFF
    n ^= n >> 16
    return n / 0xFFFFFFFF


def _smooth(t: float) -> float:
    return t * t * (3.0 - 2.0 * t)


def _noise3(x: float, y: float, z: float, seed: int) -> float:
    x0, y0, z0 = math.floor(x), math.floor(y), math.floor(z)
    tx, ty, tz = _smooth(x - x0), _smooth(y - y0), _smooth(z - z0)

    def h(ix, iy, iz):
        return _hash3(ix, iy, iz, seed)

    c000 = h(x0, y0, z0); c100 = h(x0 + 1, y0, z0)
    c010 = h(x0, y0 + 1, z0); c110 = h(x0 + 1, y0 + 1, z0)
    c001 = h(x0, y0, z0 + 1); c101 = h(x0 + 1, y0, z0 + 1)
    c011 = h(x0, y0 + 1, z0 + 1); c111 = h(x0 + 1, y0 + 1, z0 + 1)
    x00 = c000 + (c100 - c000) * tx; x10 = c010 + (c110 - c010) * tx
    x01 = c001 + (c101 - c001) * tx; x11 = c011 + (c111 - c011) * tx
    y0v = x00 + (x10 - x00) * ty; y1v = x01 + (x11 - x01) * ty
    return y0v + (y1v - y0v) * tz


def _fbm3(x: float, y: float, z: float, seed: int, octaves: int = 4) -> float:
    total = amplitude = 0.0
    frequency = 1.0
    norm = 0.0
    for index in range(octaves):
        total += _noise3(x * frequency, y * frequency, z * frequency, seed + index * 911)
        norm += amplitude
        amplitude = 0.5 if index == 0 else amplitude * 0.5
        frequency *= 2.0
    # Keep the first octave meaningful even though norm starts at zero.
    if norm <= 0.0:
        return _noise3(x, y, z, seed)
    return total / max(1.0, norm)


class CavePass:
    """Constrained 3D cave pass driven by terrain height and multi-scale noise."""

    def __init__(self, level, dimension: str = "minecraft:overworld", seed: int = 1337):
        if Block is None:
            raise RuntimeError("amulet-core is required for caves")
        self.level = level
        self.dimension = dimension
        self.seed = int(seed)
        wrapper = getattr(level, "level_wrapper", None)
        self.version = (getattr(wrapper, "platform", "java"), getattr(wrapper, "max_world_version", getattr(wrapper, "version", (1, 20, 4))))
        self._air = Block("minecraft", "air")

    def _surface(self, x: int, z: int, base_y: int, mountain_height: int, roughness: float, height_fn) -> int:
        return int(height_fn(x, z, base_y, mountain_height, roughness))

    def carve(self, center: tuple[int, int, int], radius: int, base_y: int, mountain_height: int, roughness: float, height_fn) -> CaveReport:
        cx, _, cz = center
        radius = max(16, min(int(radius), 96))
        changed = tunnels = caverns = 0

        for x in range(cx - radius, cx + radius + 1, 2):
            for z in range(cz - radius, cz + radius + 1, 2):
                dx, dz = x - cx, z - cz
                if math.hypot(dx, dz) > radius:
                    continue
                surface = self._surface(dx, dz, base_y, mountain_height, roughness, height_fn)
                if surface <= base_y + 12:
                    continue

                max_depth = min(surface - 6, base_y + int(mountain_height * 0.72))
                min_depth = base_y + 5
                for y in range(min_depth, max_depth, 2):
                    rel_y = (y - base_y) / max(1.0, mountain_height)
                    if rel_y < 0.10:
                        continue
                    cave = _fbm3(dx / 24.0, y / 21.0, dz / 24.0, self.seed + 5001, 4)
                    tunnel = _noise3(dx / 13.0, y / 15.0, dz / 13.0, self.seed + 7003)
                    cavern = fbm(dx / 70.0, dz / 70.0, self.seed + 8309, 3)
                    threshold = 0.765 - min(0.08, cavern * 0.05)
                    if cave > threshold and tunnel > 0.47:
                        self.level.set_version_block(x, y, z, self.dimension, self.version, self._air)
                        changed += 1
                        if cave > 0.86:
                            caverns += 1
                        else:
                            tunnels += 1

        return CaveReport(changed, tunnels, caverns)
