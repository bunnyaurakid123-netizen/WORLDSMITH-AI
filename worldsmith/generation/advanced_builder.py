from __future__ import annotations

from .bridges import BridgeBuilder
from .builder import BuildResult, WorldBuilder
from .caves import CavePass
from .decoration import ArchitectureFinisher
from .landscape import LandscapingPass
from .primitive_ops import PrimitiveOperationCompiler
from .redstone import RedstoneEngineer
from .settlement import compose_settlement
from .styles import resolve_style


class AdvancedWorldBuilder(WorldBuilder):
    """AAA generation pipeline with terrain, settlements, style-aware architecture and functional systems."""

    @staticmethod
    def _styled_floor_roof(builder, x: int, y: int, z: int, w: int, d: int, h: int, palette) -> int:
        changed = 0
        for xx in range(x - w // 2 + 1, x + (w + 1) // 2 - 1):
            for zz in range(z - d // 2 + 1, z + (d + 1) // 2 - 1):
                builder.put(xx, y + 1, zz, palette.floor)
                builder.put(xx, y + h + 1, zz, palette.roof)
                changed += 2
        return changed

    @staticmethod
    def _styled_windows_door(builder, x: int, y: int, z: int, w: int, d: int, h: int, palette) -> int:
        changed = 0
        window_y = y + max(2, h // 2)
        for px, py, pz in ((x - w // 2, window_y, z), (x + w // 2, window_y, z), (x, window_y, z - d // 2), (x, window_y, z + d // 2)):
            builder.put(px, py, pz, palette.glass)
            changed += 1
        builder.put(x, y + 2, z - d // 2, palette.door)
        return changed + 1

    @staticmethod
    def _styled_tower(builder, x: int, y: int, z: int, r: int, h: int, palette) -> int:
        changed = 0
        r = max(2, int(r))
        for yy in range(y + 1, y + h + 1):
            for dx in range(-r, r + 1):
                for dz in range(-r, r + 1):
                    dist2 = dx * dx + dz * dz
                    if dist2 <= r * r and dist2 >= max(1, (r - 1) ** 2):
                        builder.put(x + dx, yy, z + dz, palette.wall)
                        changed += 1
        for dx in range(-r, r + 1):
            for dz in range(-r, r + 1):
                if dx * dx + dz * dz <= (r + 1) ** 2:
                    builder.put(x + dx, y + h + 1, z + dz, palette.trim)
                    changed += 1
        return changed

    def common_build(self, b: dict) -> BuildResult:
        result = BuildResult()
        x, y, z = int(b["x"]), int(b["y"]), int(b["z"])
        w, d, h = int(b["width"]), int(b["depth"]), int(b["height"])
        kind = str(b.get("type", "house")).lower()
        palette = resolve_style(b.get("style", "medieval"))
        result.blocks_changed += self.foundation(x, y, z, w, d, palette.foundation)
        result.blocks_changed += self.shell(x, y, z, w, d, h, palette.wall)
        result.blocks_changed += self._styled_floor_roof(self, x, y, z, w, d, h, palette)
        result.blocks_changed += self._styled_windows_door(self, x, y, z, w, d, h, palette)
        for px, pz in ((x - w // 2 + 1, z - d // 2 + 1), (x + w // 2 - 1, z - d // 2 + 1), (x - w // 2 + 1, z + d // 2 - 1), (x + w // 2 - 1, z + d // 2 - 1)):
            for yy in range(y + 2, y + h + 1):
                self.put(px, yy, pz, palette.trim)
                result.blocks_changed += 1
        if b.get("interior", True):
            result.interiors_changed += self.interior(x, y, z, w, d, h, kind)
        if kind in {"tower", "watchtower"}:
            result.blocks_changed += self._styled_tower(self, x, y, z, max(2, w // 4), h + 5, palette)
        if b.get("redstone"):
            result.systems_changed += self.redstone_gate(x, y + 1, z - d // 2 - 1)
        result.structures_changed += 1
        return result

    def castle(self, b: dict) -> BuildResult:
        result = BuildResult()
        x, y, z = int(b["x"]), int(b["y"]), int(b["z"])
        w, d, h = int(b["width"]), int(b["depth"]), int(b["height"])
        palette = resolve_style(b.get("style", "medieval"))
        result.blocks_changed += self.foundation(x, y, z, w, d, palette.foundation)
        result.blocks_changed += self.shell(x, y, z, w, d, h, palette.wall)
        result.blocks_changed += self._styled_floor_roof(self, x, y, z, w, d, h, palette)
        result.blocks_changed += self._styled_windows_door(self, x, y, z, w, d, h, palette)
        tower_r = max(2, w // 8)
        for tx, tz in ((x - w // 2 + 2, z - d // 2 + 2), (x + w // 2 - 2, z - d // 2 + 2), (x - w // 2 + 2, z + d // 2 - 2), (x + w // 2 - 2, z + d // 2 - 2)):
            result.blocks_changed += self._styled_tower(self, tx, y, tz, tower_r, h + 6, palette)
        for dx in range(-2, 3):
            for yy in range(y + 2, y + h + 2):
                self.put(x + dx, yy, z - d // 2 - 1, palette.trim)
                result.blocks_changed += 1
        result.interiors_changed += self.interior(x, y, z, w, d, h, "castle")
        if b.get("redstone"):
            result.systems_changed += self.redstone_gate(x, y + 1, z - d // 2 - 2)
        result.structures_changed += 1
        return result

    def _compose_group(self, b: dict, scale: str) -> BuildResult:
        result = BuildResult()
        x, y, z = int(b["x"]), int(b["y"]), int(b["z"])
        radius = max(14, min(58, max(int(b.get("width", 32)), int(b.get("depth", 32))) // 2))
        style = str(b.get("style", "medieval"))
        layout = compose_settlement((x, y, z), radius, style, self.seed + x * 17 + z * 31, scale)
        for structure in layout.structures + layout.landmarks:
            child = dict(structure)
            child_kind = str(child.get("type", "house")).lower()
            cr = self.castle(child) if child_kind in {"castle", "fortress", "palace", "keep"} else self.common_build(child)
            result.blocks_changed += cr.blocks_changed
            result.roads_changed += cr.roads_changed
            result.systems_changed += cr.systems_changed
            result.structures_changed += cr.structures_changed
            result.interiors_changed += cr.interiors_changed
        for road in layout.roads:
            result.roads_changed += self.road(int(road["x1"]), int(road["z1"]), int(road["x2"]), int(road["z2"]), int(road["y"]), int(road["width"]))
        return result

    def village(self, b: dict) -> BuildResult:
        return self._compose_group(b, "village")

    def city(self, b: dict) -> BuildResult:
        return self._compose_group(b, "city")

    def build(self, plan: dict) -> BuildResult:
        result = BuildResult()
        self.seed = int(plan.get("seed", self.seed))
        cx, cy, cz = [int(v) for v in plan.get("center", [0, 100, 0])]
        terrain = plan.get("terrain", {})
        radius = int(terrain.get("radius", 96)); mountain_height = int(terrain.get("mountain_height", 80)); roughness = float(terrain.get("roughness", 1.0))
        if terrain.get("enabled", True):
            changed, columns = self.generate_terrain(cx, cz, radius, cy, mountain_height, roughness, bool(terrain.get("water", True)), False)
            result.blocks_changed += changed; result.terrain_columns += columns
        if terrain.get("caves", True):
            result.blocks_changed += CavePass(self.level, self.dimension, self.seed).carve((cx, cy, cz), radius, cy, mountain_height, roughness, self.height_at).blocks_changed
        if terrain.get("vegetation", True):
            result.blocks_changed += LandscapingPass(self.level, self.dimension, self.seed).apply((cx, cy, cz), radius, cy, mountain_height, roughness, str(plan.get("style", "natural")).lower()).blocks_changed
        for road in plan.get("roads", [])[:48]:
            result.roads_changed += self.road(int(road.get("x1", cx)), int(road.get("z1", cz)), int(road.get("x2", cx)), int(road.get("z2", cz)), int(road.get("y", cy + 3)), int(road.get("width", 3)))
        bridge_builder = BridgeBuilder(self.level, self.dimension)
        for bridge in plan.get("bridges", [])[:16]:
            report = bridge_builder.build(bridge); result.blocks_changed += report.blocks_changed; result.roads_changed += report.deck_blocks
        for build in plan.get("builds", [])[:24]:
            kind = str(build.get("type", "house")).lower()
            if kind in {"castle", "fortress", "palace", "keep"}: built = self.castle(build)
            elif kind in {"village", "settlement"}: built = self.village(build)
            elif kind in {"city", "town"}: built = self.city(build)
            else: built = self.common_build(build)
            result.blocks_changed += built.blocks_changed; result.roads_changed += built.roads_changed; result.systems_changed += built.systems_changed; result.structures_changed += built.structures_changed; result.interiors_changed += built.interiors_changed
        finisher = ArchitectureFinisher(self.level, self.dimension)
        for build in plan.get("builds", [])[:24]:
            report = finisher.finish(build); result.blocks_changed += report.blocks_changed; result.interiors_changed += report.interior_blocks
        if plan.get("operations"):
            result.blocks_changed += PrimitiveOperationCompiler(self.level, self.dimension).apply(plan["operations"]).blocks_changed
        return result

    def redstone_gate(self, x: int, y: int, z: int) -> int:
        report = RedstoneEngineer(self.level, self.dimension).gate(x, y, z)
        if not report.valid:
            raise RuntimeError(report.message)
        return report.blocks_changed
