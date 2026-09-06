from __future__ import annotations

import math


class PreviewScene:
    """CPU-side preview model shared by the renderer and editor tooling."""

    def __init__(self, plan: dict | None = None) -> None:
        self.plan = plan or {}

    def set_plan(self, plan: dict | None) -> None:
        self.plan = plan or {}

    def terrain_vertices(self) -> list[list[tuple[float, float, float]]]:
        terrain = self.plan.get("terrain", {})
        radius = max(16, min(int(terrain.get("radius", 96)), 192))
        step = max(4, radius // 24)
        mountain = float(terrain.get("mountain_height", 80))
        seed = int(self.plan.get("seed", 1337))
        rows: list[list[tuple[float, float, float]]] = []
        for z in range(-radius, radius + 1, step):
            row = []
            for x in range(-radius, radius + 1, step):
                nx, nz = x / radius, z / radius
                fall = max(0.0, 1.0 - math.hypot(nx, nz) ** 3)
                macro = math.sin((x + seed % 97) / 23.0) * math.cos((z - seed % 71) / 31.0)
                detail = math.sin((x - z) / 67.0)
                height = (0.48 + 0.28 * macro + 0.24 * detail) * fall * mountain
                row.append((float(x), height, float(z)))
            rows.append(row)
        return rows

    def objects(self) -> list[dict]:
        center = self.plan.get("center", [0, 100, 0])
        result = []
        for item in self.plan.get("builds", [])[:64]:
            result.append({
                "type": item.get("type", "structure"),
                "x": int(item.get("x", center[0])) - center[0],
                "y": int(item.get("y", center[1])) - center[1],
                "z": int(item.get("z", center[2])) - center[2],
                "width": max(3, min(96, int(item.get("width", 10)))),
                "depth": max(3, min(96, int(item.get("depth", 10)))),
                "height": max(3, min(128, int(item.get("height", 10)))),
            })
        return result
