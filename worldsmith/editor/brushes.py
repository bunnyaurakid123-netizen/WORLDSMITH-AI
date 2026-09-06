from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .transactions import BlockState, EditTransaction


@dataclass(frozen=True)
class BrushResult:
    changed: int
    bounds: tuple[int, int, int, int, int, int]


def _range(a: int, b: int) -> range:
    return range(min(a, b), max(a, b) + 1)


def fill_box(transaction: EditTransaction, x1: int, y1: int, z1: int, x2: int, y2: int, z2: int, block: BlockState) -> BrushResult:
    changed = 0
    for x in _range(x1, x2):
        for y in _range(y1, y2):
            for z in _range(z1, z2):
                changed += int(transaction.record(x, y, z, block))
    return BrushResult(changed, (min(x1, x2), min(y1, y2), min(z1, z2), max(x1, x2), max(y1, y2), max(z1, z2)))


def hollow_box(transaction: EditTransaction, x1: int, y1: int, z1: int, x2: int, y2: int, z2: int, block: BlockState) -> BrushResult:
    changed = 0
    xs, ys, zs = _range(x1, x2), _range(y1, y2), _range(z1, z2)
    for x in xs:
        for y in ys:
            for z in zs:
                edge = x in (min(x1, x2), max(x1, x2)) or y in (min(y1, y2), max(y1, y2)) or z in (min(z1, z2), max(z1, z2))
                if edge:
                    changed += int(transaction.record(x, y, z, block))
    return BrushResult(changed, (min(x1, x2), min(y1, y2), min(z1, z2), max(x1, x2), max(y1, y2), max(z1, z2)))


def sphere(transaction: EditTransaction, cx: int, cy: int, cz: int, radius: int, block: BlockState) -> BrushResult:
    radius = max(0, int(radius))
    changed = 0
    for x in range(cx - radius, cx + radius + 1):
        for y in range(cy - radius, cy + radius + 1):
            for z in range(cz - radius, cz + radius + 1):
                if (x - cx) ** 2 + (y - cy) ** 2 + (z - cz) ** 2 <= radius ** 2:
                    changed += int(transaction.record(x, y, z, block))
    return BrushResult(changed, (cx-radius, cy-radius, cz-radius, cx+radius, cy+radius, cz+radius))


def cylinder(transaction: EditTransaction, cx: int, cy: int, cz: int, radius: int, height: int, block: BlockState) -> BrushResult:
    radius = max(0, int(radius)); height = max(0, int(height)); changed = 0
    for y in range(cy, cy + height):
        for x in range(cx - radius, cx + radius + 1):
            for z in range(cz - radius, cz + radius + 1):
                if (x - cx) ** 2 + (z - cz) ** 2 <= radius ** 2:
                    changed += int(transaction.record(x, y, z, block))
    return BrushResult(changed, (cx-radius, cy, cz-radius, cx+radius, cy+height-1, cz+radius))
