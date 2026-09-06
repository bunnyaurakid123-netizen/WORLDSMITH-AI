from __future__ import annotations

from dataclasses import dataclass

from .scene import SceneDocument, SceneObject

@dataclass
class AddObjectCommand:
    document: SceneDocument
    obj: SceneObject
    def redo(self) -> None: self.document.add(self.obj)
    def undo(self) -> None:
        if self.obj.id in self.document.objects: self.document.remove(self.obj.id)

@dataclass
class DeleteObjectCommand:
    document: SceneDocument
    obj: SceneObject
    def redo(self) -> None:
        if self.obj.id in self.document.objects: self.document.remove(self.obj.id)
    def undo(self) -> None:
        if self.obj.id not in self.document.objects: self.document.add(self.obj)

@dataclass
class MoveObjectCommand:
    document: SceneDocument
    object_id: str
    before: dict[str, float]
    after: dict[str, float]
    def _apply(self, values: dict[str, float]) -> None:
        obj = self.document.get(self.object_id)
        if obj is not None:
            obj.transform.update(values)
            self.document.dirty = True
    def redo(self) -> None: self._apply(self.after)
    def undo(self) -> None: self._apply(self.before)

class CommandStack:
    def __init__(self) -> None: self._undo=[]; self._redo=[]
    @property
    def can_undo(self) -> bool: return bool(self._undo)
    @property
    def can_redo(self) -> bool: return bool(self._redo)
    def push(self, command) -> None:
        command.redo(); self._undo.append(command); self._redo.clear()
    def undo(self) -> None:
        if self._undo:
            command=self._undo.pop(); command.undo(); self._redo.append(command)
    def redo(self) -> None:
        if self._redo:
            command=self._redo.pop(); command.redo(); self._undo.append(command)
    def clear(self) -> None: self._undo.clear(); self._redo.clear()
