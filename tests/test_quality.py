from worldsmith.generation.quality import inspect_plan, repair_plan


def test_quality_detects_missing_roads_and_redstone():
    plan = {
        "center": [0, 100, 0],
        "terrain": {"water": True},
        "builds": [
            {"type": "castle", "x": 0, "y": 100, "z": 0, "width": 30, "depth": 30, "height": 25, "interior": False, "redstone": False},
            {"type": "house", "x": 8, "y": 100, "z": 8, "width": 8, "depth": 8, "height": 8, "interior": False, "redstone": False},
        ],
        "roads": [],
        "bridges": [],
    }
    issues = inspect_plan(plan)
    messages = " | ".join(issue.message for issue in issues)
    assert "road" in messages.lower()
    assert "redstone" in messages.lower()


def test_repair_adds_roads_and_fortification_intent():
    plan = {
        "center": [0, 100, 0],
        "terrain": {},
        "builds": [
            {"type": "castle", "x": 0, "y": 100, "z": 0, "width": 30, "depth": 30, "height": 25, "interior": False, "redstone": False},
            {"type": "house", "x": 40, "y": 100, "z": 0, "width": 8, "depth": 8, "height": 8},
        ],
        "roads": [],
        "bridges": [],
    }
    repaired, _ = repair_plan(plan)
    assert repaired["roads"]
    assert repaired["builds"][0]["interior"] is True
    assert repaired["builds"][0]["redstone"] is True
