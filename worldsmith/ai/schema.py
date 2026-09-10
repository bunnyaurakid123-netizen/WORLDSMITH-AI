from __future__ import annotations


_ARCHITECTURE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "roof": {"type": "string"},
        "window_style": {"type": "string"},
        "chimney": {"type": "boolean"},
        "balcony": {"type": "boolean"},
        "courtyard": {"type": "boolean"},
        "room_types": {"type": "array", "items": {"type": "string"}},
    },
}


WORLD_PLAN_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "summary": {"type": "string"},
        "style": {"type": "string"},
        "seed": {"type": "integer"},
        "center": {"type": "array", "items": {"type": "integer"}, "minItems": 3, "maxItems": 3},
        "safety": {
            "type": "object", "additionalProperties": False,
            "properties": {"preserve_existing": {"type": "boolean"}, "allow_terrain_regeneration": {"type": "boolean"}, "max_blocks": {"type": "integer"}},
            "required": ["preserve_existing", "allow_terrain_regeneration", "max_blocks"],
        },
        "terrain": {
            "type": "object", "additionalProperties": False,
            "properties": {"enabled": {"type": "boolean"}, "radius": {"type": "integer"}, "mountain_height": {"type": "integer"}, "roughness": {"type": "number"}, "water": {"type": "boolean"}, "vegetation": {"type": "boolean"}, "caves": {"type": "boolean"}},
            "required": ["enabled", "radius", "mountain_height", "roughness", "water", "vegetation", "caves"],
        },
        "builds": {"type": "array", "items": {
            "type": "object", "additionalProperties": False,
            "properties": {
                "type": {"type": "string"}, "x": {"type": "integer"}, "y": {"type": "integer"}, "z": {"type": "integer"},
                "width": {"type": "integer"}, "depth": {"type": "integer"}, "height": {"type": "integer"}, "style": {"type": "string"},
                "interior": {"type": "boolean"}, "redstone": {"type": "boolean"}, "architecture": _ARCHITECTURE_SCHEMA,
            },
            "required": ["type", "x", "y", "z", "width", "depth", "height", "style", "interior", "redstone"],
        }},
        "roads": {"type": "array", "items": {"type": "object", "additionalProperties": False, "properties": {
            "x1": {"type": "integer"}, "z1": {"type": "integer"}, "x2": {"type": "integer"}, "z2": {"type": "integer"}, "y": {"type": "integer"}, "width": {"type": "integer"},
        }, "required": ["x1", "z1", "x2", "z2", "y", "width"]}},
        "bridges": {"type": "array", "items": {"type": "object", "additionalProperties": False, "properties": {
            "type": {"type": "string"}, "x": {"type": "integer"}, "y": {"type": "integer"}, "z": {"type": "integer"}, "x2": {"type": "integer"}, "z2": {"type": "integer"}, "width": {"type": "integer"},
        }, "required": ["type", "x", "y", "z", "x2", "z2", "width"]}},
        "operations": {"type": "array", "items": {"type": "object", "additionalProperties": False, "properties": {
            "op": {"type": "string"}, "block": {"type": "string"}, "x1": {"type": "integer"}, "y1": {"type": "integer"}, "z1": {"type": "integer"},
            "x2": {"type": "integer"}, "y2": {"type": "integer"}, "z2": {"type": "integer"}, "x": {"type": "integer"}, "y": {"type": "integer"}, "z": {"type": "integer"},
            "radius": {"type": "integer"}, "height": {"type": "integer"},
        }, "required": ["op", "block", "x1", "y1", "z1", "x2", "y2", "z2", "x", "y", "z", "radius", "height"]}},
        "notes": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["summary", "style", "seed", "center", "safety", "terrain", "builds", "roads", "bridges", "operations", "notes"],
}


def strict_schema() -> dict:
    return {**WORLD_PLAN_SCHEMA}
