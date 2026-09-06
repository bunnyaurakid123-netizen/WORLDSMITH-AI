from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class BlockState:
    """Version-independent description of a block and optional block entity."""

    block: Any
    entity: Any = None


@dataclass(frozen=True)
class BlockChange:
    x: int
    y: int
    z: int
    before: BlockState
    after: BlockState


class EditTransaction:
    """Collect, apply, undo, and redo voxel changes as one atomic edit."""

    def __init__(self, adapter):
        self.adapter = adapter
        self.changes: list[BlockChange] = []
        self._committed = False

    def record(self, x: int, y: int, z: int, after: BlockState) -> bool:
        before = self.adapter.get_block(x, y, z)
        if before == after:
            return False
        self.changes.append(BlockChange(int(x), int(y), int(z), before, after))
        return True

    def apply(self) -> int:
        if self._committed:
            raise RuntimeError("Transaction has already been applied")
        applied: list[BlockChange] = []
        try:
            for change in self.changes:
                self.adapter.set_block(change.x, change.y, change.z, change.after)
                applied.append(change)
        except Exception:
            for change in reversed(applied):
                self.adapter.set_block(change.x, change.y, change.z, change.before)
            raise
        self._committed = True
        return len(applied)

    def undo(self) -> int:
        if not self._committed:
            raise RuntimeError("Transaction has not been applied")
        for change in reversed(self.changes):
            self.adapter.set_block(change.x, change.y, change.z, change.before)
        self._committed = False
        return len(self.changes)

    def redo(self) -> int:
        if self._committed:
            raise RuntimeError("Transaction is already applied")
        for change in self.changes:
            self.adapter.set_block(change.x, change.y, change.z, change.after)
        self._committed = True
        return len(self.changes)


class EditHistory:
    """Bounded undo/redo stack for WorldSmith edits."""

    def __init__(self, adapter, limit: int = 100):
        self.adapter = adapter
        self.limit = max(1, int(limit))
        self.undo_stack: list[EditTransaction] = []
        self.redo_stack: list[EditTransaction] = []

    def commit(self, transaction: EditTransaction) -> int:
        changed = transaction.apply()
        if changed:
            self.undo_stack.append(transaction)
            if len(self.undo_stack) > self.limit:
                self.undo_stack.pop(0)
            self.redo_stack.clear()
        return changed

    def undo(self) -> int:
        if not self.undo_stack:
            return 0
        transaction = self.undo_stack.pop()
        changed = transaction.undo()
        self.redo_stack.append(transaction)
        return changed

    def redo(self) -> int:
        if not self.redo_stack:
            return 0
        transaction = self.redo_stack.pop()
        changed = transaction.redo()
        self.undo_stack.append(transaction)
        return changed
