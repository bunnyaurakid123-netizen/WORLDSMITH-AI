from __future__ import annotations

from dataclasses import dataclass

@dataclass(frozen=True)
class ValidationIssue:
    severity: str
    code: str
    message: str
    object_id: str | None = None

def validate_scene(document, world_bounds=None):
    issues=[]
    objects=list(document.objects.values())
    for obj in objects:
        b=obj.bounds().normalized()
        if b.x1<=b.x0 or b.y1<=b.y0 or b.z1<=b.z0:
            issues.append(ValidationIssue('error','empty-bounds',f'{obj.name} has zero or negative size',obj.id))
        if any(abs(v)>30_000_000 for v in (b.x0,b.x1,b.z0,b.z1)):
            issues.append(ValidationIssue('error','coordinate-limit',f'{obj.name} exceeds horizontal coordinate limits',obj.id))
        if b.y0 < -2048 or b.y1 > 2048:
            issues.append(ValidationIssue('warning','height-limit',f'{obj.name} exceeds the editor height range',obj.id))
    for i,a in enumerate(objects):
        for b in objects[i+1:]:
            if a.bounds().intersects(b.bounds(), margin=-0.5):
                issues.append(ValidationIssue('warning','overlap',f'{a.name} overlaps {b.name}',b.id))
    if world_bounds:
        x0,y0,z0,x1,y1,z1=world_bounds
        for obj in objects:
            b=obj.bounds()
            if b.x0<x0 or b.y0<y0 or b.z0<z0 or b.x1>x1 or b.y1>y1 or b.z1>z1:
                issues.append(ValidationIssue('error','outside-region',f'{obj.name} leaves the active editing region',obj.id))
    return issues
