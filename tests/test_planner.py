from worldsmith.ai.orchestrator import built_in_plan
from worldsmith.planner import Planner


def test_fallback_plan():
    p = built_in_plan("mountains", (0, 100, 0), 96)
    assert p["terrain"]["radius"] == 96
    assert p["terrain"]["water"] is True
    assert len(p["builds"]) <= 24


def test_sanitize_caps_builds_and_dimensions():
    class Fake:
        def plan(self, *a, **k):
            from worldsmith.ai.orchestrator import EnsembleResult
            return EnsembleResult(
                {
                    "center": [0, 100, 0],
                    "builds": [{"x": 0, "y": 100, "z": 0, "width": 999, "depth": 999, "height": 999}] * 50,
                },
                [],
                [],
                [],
            )

    p = Planner(Fake()).make_plan("x", "y").plan
    assert len(p["builds"]) == 24
    assert p["builds"][0]["width"] == 64
    assert p["builds"][0]["depth"] == 64
    assert p["builds"][0]["height"] == 64


def test_sanitize_bridges_and_terrain():
    class Fake:
        def plan(self, *a, **k):
            from worldsmith.ai.orchestrator import EnsembleResult
            return EnsembleResult(
                {
                    "terrain": {"radius": 999, "mountain_height": -5, "roughness": 50},
                    "bridges": [{"x": 1, "z": 2, "x2": 3, "z2": 4, "width": 99}],
                },
                [],
                [],
                [],
            )

    plan = Planner(Fake()).make_plan("x", "y").plan
    assert plan["terrain"]["radius"] == 128
    assert plan["terrain"]["mountain_height"] == 8
    assert plan["terrain"]["roughness"] == 1.8
    assert plan["bridges"][0]["width"] == 7
