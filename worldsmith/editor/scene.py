from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

@dataclass
class AABB:
    x0: float
    y0: float
    z0: float
    x1: float
    y1: float
    z1: float

    def normalized(self) -> "AABB":
        return AABB(min(self.x0, self.x1), min(self.y0, self.y1), min(self.z0, self.z1), max(self.x0, self.x1), max(self.y0, self.y1), max(self.z0, self.z1))

    def intersects(self, other: "AABB", margin: float = 0.0) -> bool:
        a, b = self.normalized(), other.normalized()
        return not (a.x1 + margin < b.x0 or b.x1 + margin < a.x0 or a.y1 + margin < b.y0 or b.y1 + margin < a.y0 or a.z1 + margin < b.z0 or b.z1 + margin < a.z0)

    def contains_point(self, x: float, y: float, z: float) -> bool:
        a = self.normalized()
        return a.x0 <= x <= a.x1 and a.y0 <= y <= a.y1 and a.z0 <= z <= a.z1

@dataclass
class SceneObject:
    id: str
    kind: str
    name: str
    transform: dict[str, float] = field(default_factory=lambda: {"x": 0.0, "y": 0.0, "z": 0.0})
    size: dict[str, float] = field(default_factory=lambda: {"x": 1.0, "y": 1.0, "z": 1.0})
    style: str = "default"
    metadata: dict[str, Any] = field(default_factory=dict)
    locked: bool = False
    visible: bool = True

    def bounds(self) -> AABB:
        x, y, z = self.transform["x"], self.transform["y"], self.transform["z"]
        sx, sy, sz = self.size["x"], self.size["y"], self.size["z"]
        return AABB(x - sx / 2, y, z - sz / 2, x + sx / 2, y + sy, z + sz / 2)

class SceneDocument:
    def __init__(self) -> None:
        self.objects: dict[str, SceneObject] = {}
        self.selection: list[str] = []
        self.dirty = False
        self._counter = 0

    def new_id(self, prefix: str = "object") -> str:
        self._counter += 1
        return f"{prefix}-{self._counter:04d}"

    def add(self, obj: SceneObject) -> None:
        if obj.id in self.objects:
            raise ValueError(f"Duplicate scene object id: {obj.id}")
        self.objects[obj.id] = obj
        self.dirty = True

    def remove(self, object_id: str) -> SceneObject:
        obj = self.objects.pop(object_id)
        self.selection = [x for x in self.selection if x != object_id]
        self.dirty = True
        return obj

    def get(self, object_id: str) -> SceneObject | None:
        return self.objects.get(object_id)

    def set_selection(self, ids: list[str]) -> None:
        self.selection = [x for x in ids if x in self.objects]

    def selected(self) -> list[SceneObject]:
        return [self.objects[x] for x in self.selection if x in self.objects]

    def overlaps(self, object_id: str, margin: float = 0.0) -> list[SceneObject]:
        target = self.objects[object_id]
        return [o for oid, o in self.objects.items() if oid != object_id and target.bounds().intersects(o.bounds(), margin)]

    def snapshot(self) -> dict[str, Any]:
        return {"objects": [o.__dict__.copy() for o in self.objects.values()], "selection": list(self.selection)}

    @classmethod
    def from_snapshot(cls, snapshot: dict[str, Any]) -> "SceneDocument":
        doc = cls()
        for raw in snapshot.get("objects", []):
            doc.add(SceneObject(**raw))
        doc.set_selection(snapshot.get("selection", []))
        doc.dirty = False
        return doc
