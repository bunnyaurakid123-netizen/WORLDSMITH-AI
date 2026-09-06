from __future__ import annotations

import math
import random
from dataclasses import dataclass


@dataclass(frozen=True)
class SettlementPlan:
    structures: tuple[dict, ...]
    roads: tuple[dict, ...]
    landmarks: tuple[dict, ...]


def compose_settlement(center: tuple[int, int, int], radius: int, style: str, seed: int, scale: str = "city") -> SettlementPlan:
    """Create a deterministic civilization layout with districts and a road hierarchy."""
    cx, cy, cz = center
    rng = random.Random(seed)
    radius = max(12, min(int(radius), 60))
    scale = scale.lower()
    count = 12 if scale in {"city", "town"} else 8
    structures: list[dict] = []
    roads: list[dict] = []
    landmarks: list[dict] = []

    # Civic core.
    core_type = "castle" if scale == "city" else "town_hall"
    structures.append({
        "type": core_type, "x": cx, "y": cy, "z": cz,
        "width": min(31, radius // 2 + 13), "depth": min(31, radius // 2 + 13), "height": 24,
        "style": style, "interior": True, "redstone": scale == "city",
    })

    district_types = ["house", "house", "tavern", "blacksmith", "warehouse", "temple", "house", "farm"]
    for index in range(count):
        angle = (math.tau * index / count) + rng.uniform(-0.12, 0.12)
        distance = radius * rng.uniform(0.46, 0.88)
        x = round(cx + math.cos(angle) * distance)
        z = round(cz + math.sin(angle) * distance)
        kind = district_types[index % len(district_types)]
        size = 7 if kind in {"house", "farm"} else 9 if kind in {"tavern", "blacksmith", "warehouse"} else 11
        structures.append({
            "type": kind, "x": x, "y": cy, "z": z,
            "width": size + rng.randrange(0, 4), "depth": size + rng.randrange(0, 4),
            "height": 7 + rng.randrange(0, 6), "style": style,
            "interior": True, "redstone": False,
        })
        roads.append({"x1": cx, "z1": cz, "x2": x, "z2": z, "y": cy + 3, "width": 2 if index % 3 else 3})

    # Ring roads connect districts without making everything converge on the same line.
    ring_points: list[tuple[int, int]] = []
    for index in range(8):
        angle = math.tau * index / 8.0
        ring_points.append((round(cx + math.cos(angle) * radius * 0.66), round(cz + math.sin(angle) * radius * 0.66)))
    for index, (x1, z1) in enumerate(ring_points):
        x2, z2 = ring_points[(index + 1) % len(ring_points)]
        roads.append({"x1": x1, "z1": z1, "x2": x2, "z2": z2, "y": cy + 3, "width": 3})

    landmarks.extend([
        {"type": "market", "x": cx + radius // 4, "y": cy + 2, "z": cz - radius // 5, "width": 15, "depth": 11, "height": 7, "style": style, "interior": True, "redstone": False},
        {"type": "gate", "x": cx + radius, "y": cy + 2, "z": cz, "width": 9, "depth": 7, "height": 13, "style": style, "interior": False, "redstone": True},
    ])
    return SettlementPlan(tuple(structures), tuple(roads), tuple(landmarks))
