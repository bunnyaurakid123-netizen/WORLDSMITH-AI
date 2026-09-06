from __future__ import annotations

import math


def _hash2(x: int, z: int, seed: int) -> float:
    n = (x * 374761393 + z * 668265263 + seed * 1442695041) & 0xFFFFFFFF
    n = (n ^ (n >> 13)) * 1274126177 & 0xFFFFFFFF
    n ^= n >> 16
    return n / 0xFFFFFFFF


def smooth(t: float) -> float:
    return t * t * (3.0 - 2.0 * t)


def value_noise(x: float, z: float, seed: int) -> float:
    x0, z0 = math.floor(x), math.floor(z)
    tx, tz = x - x0, z - z0
    a = _hash2(x0, z0, seed)
    b = _hash2(x0 + 1, z0, seed)
    c = _hash2(x0, z0 + 1, seed)
    d = _hash2(x0 + 1, z0 + 1, seed)
    sx, sz = smooth(tx), smooth(tz)
    ab = a + (b - a) * sx
    cd = c + (d - c) * sx
    return ab + (cd - ab) * sz


def fbm(x: float, z: float, seed: int, octaves: int = 5) -> float:
    octaves = max(1, int(octaves))
    total = 0.0
    amplitude = 1.0
    frequency = 1.0
    norm = 0.0
    for i in range(octaves):
        total += value_noise(x * frequency, z * frequency, seed + i * 1013) * amplitude
        norm += amplitude
        amplitude *= 0.5
        frequency *= 2.0
    return total / norm


def ridge(x: float, z: float, seed: int) -> float:
    return 1.0 - abs(fbm(x, z, seed, 5) * 2.0 - 1.0)
