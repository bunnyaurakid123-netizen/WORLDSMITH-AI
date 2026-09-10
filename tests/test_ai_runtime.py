from worldsmith.ai.orchestrator import built_in_plan, score_plan
from worldsmith.ai.schema import WORLD_PLAN_SCHEMA
from worldsmith.generation.redstone_sim import gate_contract
from worldsmith.generation.terrain_engine import TerrainEngine


def test_world_plan_schema_contract():
    assert WORLD_PLAN_SCHEMA["type"] == "object"
    assert "terrain" in WORLD_PLAN_SCHEMA["required"]
    assert "operations" in WORLD_PLAN_SCHEMA["properties"]


def test_fallback_plan_is_composable_and_scored():
    plan = built_in_plan("Create a snowy kingdom city with a port", (10, 90, -20), 64)
    assert len(plan["builds"]) >= 6
    assert plan["terrain"]["mountain_height"] >= 80
    assert score_plan(plan) > 30


def test_terrain_is_deterministic_and_varied():
    a = TerrainEngine(1234)
    b = TerrainEngine(1234)
    samples_a = [a.sample(x, z, 100, 80, 1.0) for x, z in ((0, 0), (20, 11), (-40, 27), (75, -12))]
    samples_b = [b.sample(x, z, 100, 80, 1.0) for x, z in ((0, 0), (20, 11), (-40, 27), (75, -12))]
    assert samples_a == samples_b
    assert len({sample.height for sample in samples_a}) >= 2


def test_gate_contract_off_and_on():
    simulator = gate_contract()
    off = simulator.run({"lever": False}, ("left_piston", "right_piston"))
    on = simulator.run({"lever": True}, ("left_piston", "right_piston"))
    assert off.valid and not any(off.outputs.values())
    assert on.valid and all(on.outputs.values())
