from __future__ import annotations

from dataclasses import dataclass

from .styles import StylePalette


@dataclass(frozen=True)
class ArchitectureResult:
    blocks: int = 0
    interior: int = 0


def _put(builder, x: int, y: int, z: int, block: str, *, interior: bool = False) -> int:
    return int(bool(builder.put(x, y, z, block)))


def _line(builder, points, block: str, *, interior: bool = False) -> int:
    changed = 0
    for x, y, z in points:
        changed += _put(builder, x, y, z, block, interior=interior)
    return changed


def _gabled_roof(builder, x: int, y: int, z: int, w: int, d: int, h: int, palette: StylePalette) -> int:
    changed = 0
    half_d = max(1, d // 2)
    for layer in range(max(1, half_d)):
        roof_y = y + h + 1 + layer
        z_front = z - half_d + layer
        z_back = z + half_d - layer
        for xx in range(x - w // 2 - 1, x + (w + 1) // 2 + 1):
            changed += _put(builder, xx, roof_y, z_front, palette.stair)
            if z_back != z_front:
                changed += _put(builder, xx, roof_y, z_back, palette.stair)
    ridge_y = y + h + max(1, half_d)
    for xx in range(x - w // 2, x + (w + 1) // 2):
        changed += _put(builder, xx, ridge_y, z, palette.trim)
    return changed


def _pyramid_roof(builder, x: int, y: int, z: int, w: int, d: int, h: int, palette: StylePalette) -> int:
    changed = 0
    layers = max(1, min(w, d) // 2 + 1)
    for layer in range(layers):
        roof_y = y + h + 1 + layer
        x0, x1 = x - w // 2 + layer - 1, x + (w + 1) // 2 - layer
        z0, z1 = z - d // 2 + layer - 1, z + (d + 1) // 2 - layer
        if x0 > x1 or z0 > z1:
            break
        for xx in range(x0, x1 + 1):
            changed += _put(builder, xx, roof_y, z0, palette.stair)
            if z1 != z0:
                changed += _put(builder, xx, roof_y, z1, palette.stair)
        for zz in range(z0 + 1, z1):
            changed += _put(builder, x0, roof_y, zz, palette.stair)
            if x1 != x0:
                changed += _put(builder, x1, roof_y, zz, palette.stair)
    changed += _put(builder, x, y + h + layers + 1, z, palette.trim)
    return changed


def _flat_roof(builder, x: int, y: int, z: int, w: int, d: int, h: int, palette: StylePalette) -> int:
    changed = 0
    roof_y = y + h + 1
    for xx in range(x - w // 2 - 1, x + (w + 1) // 2 + 1):
        for zz in range(z - d // 2 - 1, z + (d + 1) // 2 + 1):
            changed += _put(builder, xx, roof_y, zz, palette.roof)
    return changed


def _windows(builder, x: int, y: int, z: int, w: int, d: int, h: int, palette: StylePalette, style: str) -> int:
    changed = 0
    window_y = y + max(2, h // 2)
    spacing = 3 if "grand" in style.lower() or w >= 18 else 4
    for xx in range(x - w // 2 + 2, x + (w + 1) // 2 - 1, spacing):
        if abs(xx - x) <= 1:
            continue
        changed += _put(builder, xx, window_y, z - d // 2, palette.glass)
        changed += _put(builder, xx, window_y, z + d // 2, palette.glass)
    for zz in range(z - d // 2 + 2, z + (d + 1) // 2 - 1, spacing):
        if abs(zz - z) <= 1:
            continue
        changed += _put(builder, x - w // 2, window_y, zz, palette.glass)
        changed += _put(builder, x + w // 2, window_y, zz, palette.glass)
    return changed


def _chimney(builder, x: int, y: int, z: int, h: int, palette: StylePalette) -> int:
    changed = 0
    for yy in range(y + h + 1, y + h + 5):
        changed += _put(builder, x, yy, z, palette.wall)
        changed += _put(builder, x + 1, yy, z, palette.wall)
    changed += _put(builder, x, y + h + 5, z, palette.trim)
    changed += _put(builder, x + 1, y + h + 5, z, palette.trim)
    return changed


def _balcony(builder, x: int, y: int, z: int, w: int, d: int, h: int, palette: StylePalette) -> int:
    changed = 0
    by = y + max(4, h // 2)
    depth = min(4, max(2, d // 4))
    for xx in range(x - max(2, w // 5), x + max(2, w // 5) + 1):
        for dz in range(-depth, 1):
            changed += _put(builder, xx, by, z - d // 2 - 1 + dz, palette.floor)
    edge_z = z - d // 2 - 1 - depth
    for xx in range(x - max(2, w // 5), x + max(2, w // 5) + 1):
        changed += _put(builder, xx, by + 1, edge_z, palette.fence)
    return changed


def _courtyard(builder, x: int, y: int, z: int, w: int, d: int, palette: StylePalette) -> int:
    if w < 16 or d < 16:
        return 0
    changed = 0
    for xx in range(x - w // 4, x + (w + 1) // 4):
        for zz in range(z - d // 4, z + (d + 1) // 4):
            changed += _put(builder, xx, y + 2, zz, palette.floor, interior=True)
    cx, cz = x, z
    changed += _put(builder, cx, y + 3, cz, palette.light, interior=True)
    for dx, dz in ((-2, 0), (2, 0), (0, -2), (0, 2)):
        changed += _put(builder, cx + dx, y + 3, cz + dz, palette.fence, interior=True)
    return changed


def _rooms(builder, x: int, y: int, z: int, w: int, d: int, h: int, palette: StylePalette, room_types: list[str]) -> int:
    changed = 0
    if w < 9 or d < 9:
        return changed
    floor_height = max(4, min(6, h - 2))
    floors = max(1, min(4, h // floor_height))
    inner_w = max(5, w - 4)
    inner_d = max(5, d - 4)
    for floor in range(floors):
        room_y = y + 2 + floor * floor_height
        changed += _put(builder, x, room_y, z, palette.light, interior=True)
        if floor == 0 and room_types:
            # Add furniture/stations according to room purpose, using blocks that exist in vanilla Java.
            offsets = [(-inner_w // 4, -inner_d // 4), (inner_w // 4, -inner_d // 4), (-inner_w // 4, inner_d // 4), (inner_w // 4, inner_d // 4)]
            for idx, room in enumerate(room_types[:4]):
                ox, oz = offsets[idx]
                kind = room.lower()
                block = "minecraft:chest"
                if "bed" in kind or "sleep" in kind:
                    block = "minecraft:bed"
                elif "forge" in kind or "smith" in kind:
                    block = "minecraft:blast_furnace"
                elif "library" in kind:
                    block = "minecraft:bookshelf"
                elif "kitchen" in kind:
                    block = "minecraft:crafting_table"
                elif "storage" in kind:
                    block = "minecraft:barrel"
                elif "portal" in kind:
                    block = "minecraft:crying_obsidian"
                changed += _put(builder, x + ox, room_y, z + oz, block, interior=True)
        if floor < floors - 1:
            for xx in range(x - inner_w // 2, x + (inner_w + 1) // 2):
                for zz in range(z - inner_d // 2, z + (inner_d + 1) // 2):
                    changed += _put(builder, xx, room_y + floor_height, zz, palette.floor, interior=True)
    return changed


def enhance_structure(builder, build: dict, palette: StylePalette, kind: str) -> ArchitectureResult:
    x, y, z = int(build["x"]), int(build["y"]), int(build["z"])
    w, d, h = int(build["width"]), int(build["depth"]), int(build["height"])
    design = build.get("architecture") if isinstance(build.get("architecture"), dict) else {}
    style = str(build.get("style", "medieval"))
    roof = str(design.get("roof", "gabled" if kind not in {"tower", "modern"} else "flat")).lower()
    blocks = 0
    interior = 0

    if roof in {"gabled", "gable", "pitched"}:
        blocks += _gabled_roof(builder, x, y, z, w, d, h, palette)
    elif roof in {"pyramid", "hip"}:
        blocks += _pyramid_roof(builder, x, y, z, w, d, h, palette)
    else:
        blocks += _flat_roof(builder, x, y, z, w, d, h, palette)

    blocks += _windows(builder, x, y, z, w, d, h, palette, str(design.get("window_style", style)))

    if bool(design.get("chimney", kind in {"house", "tavern", "blacksmith"})) and h >= 7:
        blocks += _chimney(builder, x + max(1, w // 4), y, z + max(1, d // 5), h, palette)
    if bool(design.get("balcony", kind in {"house", "castle", "palace"})) and w >= 12 and h >= 10:
        blocks += _balcony(builder, x, y, z, w, d, h, palette)
    if bool(design.get("courtyard", False)):
        interior += _courtyard(builder, x, y, z, w, d, palette)

    room_types = design.get("room_types", [])
    if isinstance(room_types, list):
        interior += _rooms(builder, x, y, z, w, d, h, palette, [str(r)[:32] for r in room_types])

    return ArchitectureResult(blocks, interior)
