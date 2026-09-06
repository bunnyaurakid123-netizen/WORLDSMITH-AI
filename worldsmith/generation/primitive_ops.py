from __future__ import annotations

from dataclasses import dataclass

from worldsmith.editor.amulet_adapter import AmuletAdapter, Palette
from worldsmith.editor.brushes import cylinder, fill_box, hollow_box, sphere
from worldsmith.editor.transactions import BlockState, EditHistory, EditTransaction


@dataclass(frozen=True)
class PrimitiveReport:
    operations: int
    blocks_changed: int


class PrimitiveOperationCompiler:
    """Compile bounded AI voxel operations into transactional edits."""

    LIMIT = 48

    def __init__(self, level, dimension: str = "minecraft:overworld"):
        self.adapter = AmuletAdapter(level, dimension)
        self.history = EditHistory(self.adapter, limit=40)

    def _block(self, value: str) -> BlockState:
        import amulet
        identifier = Palette.resolve(value)
        namespace, base = identifier.split(":", 1)
        return BlockState(amulet.api.block.Block(namespace, base))

    def apply(self, operations: list[dict]) -> PrimitiveReport:
        if len(operations) > self.LIMIT:
            raise ValueError(f"Too many primitive operations: {len(operations)} > {self.LIMIT}")

        total = 0
        used = 0
        for op in operations:
            kind = str(op.get("op", "")).lower().strip()
            block = self._block(str(op.get("block", "stone")))
            tx = EditTransaction(self.adapter)

            if kind == "fill_box":
                result = fill_box(tx, int(op["x1"]), int(op["y1"]), int(op["z1"]), int(op["x2"]), int(op["y2"]), int(op["z2"]), block)
            elif kind == "hollow_box":
                result = hollow_box(tx, int(op["x1"]), int(op["y1"]), int(op["z1"]), int(op["x2"]), int(op["y2"]), int(op["z2"]), block)
            elif kind == "sphere":
                result = sphere(tx, int(op["x"]), int(op["y"]), int(op["z"]), min(32, int(op.get("radius", 4))), block)
            elif kind == "cylinder":
                result = cylinder(tx, int(op["x"]), int(op["y"]), int(op["z"]), min(32, int(op.get("radius", 4))), min(64, int(op.get("height", 8))), block)
            else:
                raise ValueError(f"Unsupported primitive operation: {kind!r}")

            if result.changed:
                self.history.commit(tx)
                total += result.changed
            used += 1
        return PrimitiveReport(used, total)

    def undo(self) -> int:
        return self.history.undo()

    def redo(self) -> int:
        return self.history.redo()
