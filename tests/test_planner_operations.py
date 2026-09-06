from worldsmith.planner import Planner


def test_sanitizer_caps_and_accepts_primitive_operations():
    class FakeEnsemble:
        def plan(self, *args, **kwargs):
            return type("Result", (), {
                "plan": {
                    "center": [0, 100, 0],
                    "operations": [
                        {"op": "sphere", "x": 0, "y": 100, "z": 0, "radius": 99, "height": 999, "block": "stone"},
                        {"op": "not_real", "x": 999999, "y": 999999, "z": 999999},
                    ],
                    "builds": [], "roads": [], "bridges": [], "notes": [],
                }, "responses": [], "errors": [], "activity": []
            })()

    result = Planner(FakeEnsemble()).make_plan("test", "test")
    ops = result.plan["operations"]
    assert len(ops) == 1
    assert ops[0]["radius"] == 32
    assert ops[0]["height"] == 64
