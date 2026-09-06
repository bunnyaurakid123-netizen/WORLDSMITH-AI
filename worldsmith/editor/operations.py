from __future__ import annotations

from dataclasses import dataclass

from .amulet_adapter import AmuletAdapter, Palette
from .brushes import BrushResult, cylinder, fill_box, hollow_box, sphere
from .transactions import BlockState, EditHistory, EditTransaction


@dataclass(frozen=True)
class Selection:
    x1: int
    y1: int
    z1: int
    x2: int
    y2: int
    z2: int

    @property
    def volume(self) -> int:
        return (abs(self.x2 - self.x1) + 1) * (abs(self.y2 - self.y1) + 1) * (abs(self.z2 - self.z1) + 1)

    @property
    def normalized(self) -> "Selection":
        return Selection(min(self.x1, self.x2), min(self.y1, self.y2), min(self.z1, self.z2), max(self.x1, self.x2), max(self.y1, self.y2), max(self.z1, self.z2))


class VoxelEditor:
    """User-facing voxel editing operations backed by one undo/redo history."""

    MAX_SELECTION_VOLUME = 250_000

    def __init__(self, level, dimension: str = "minecraft:overworld", history_limit: int = 100):
        self.adapter = AmuletAdapter(level, dimension)
        self.history = EditHistory(self.adapter, history_limit)
        self.selection: Selection | None = None

    def select(self, selection: Selection) -> Selection:
        normalized = selection.normalized
        if normalized.volume > self.MAX_SELECTION_VOLUME:
            raise ValueError(f"Selection is too large: {normalized.volume:,} blocks > {self.MAX_SELECTION_VOLUME:,}")
        self.selection = normalized
        return self.selection

    def _transaction(self) -> EditTransaction:
        return EditTransaction(self.adapter)

    def block(self, name: str) -> BlockState:
        from amulet.api.block import Block
        identifier = Palette.resolve(name)
        namespace, base = identifier.split(":", 1)
        return BlockState(Block(namespace, base))

    def fill_selection(self, block: str) -> BrushResult:
        if self.selection is None:
            raise RuntimeError("Select a region first")
        s = self.selection
        tx = self._transaction()
        result = fill_box(tx, s.x1, s.y1, s.z1, s.x2, s.y2, s.z2, self.block(block))
        self.history.commit(tx)
        return result

    def hollow_selection(self, block: str) -> BrushResult:
        if self.selection is None:
            raise RuntimeError("Select a region first")
        s = self.selection
        tx = self._transaction()
        result = hollow_box(tx, s.x1, s.y1, s.z1, s.x2, s.y2, s.z2, self.block(block))
        self.history.commit(tx)
        return result

    def sphere_at(self, center: tuple[int, int, int], radius: int, block: str) -> BrushResult:
        radius = max(1, min(int(radius), 32))
        tx = self._transaction()
        result = sphere(tx, *center, radius, self.block(block))
        self.history.commit(tx)
        return result

    def cylinder_at(self, center: tuple[int, int, int], radius: int, height: int, block: str) -> BrushResult:
        radius = max(1, min(int(radius), 32)); height = max(1, min(int(height), 64))
        tx = self._transaction()
        result = cylinder(tx, center[0], center[1], center[2], radius, height, self.block(block))
        self.history.commit(tx)
        return result

    def undo(self) -> int:
        return self.history.undo()

    def redo(self) -> int:
        return self.history.redo()
