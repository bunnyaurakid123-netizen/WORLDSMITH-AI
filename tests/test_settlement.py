from worldsmith.generation.settlement import compose_settlement


def test_settlement_is_deterministic_and_connected():
    a = compose_settlement((0, 100, 0), 40, "medieval", 1234, "city")
    b = compose_settlement((0, 100, 0), 40, "medieval", 1234, "city")
    assert a == b
    assert len(a.structures) >= 10
    assert len(a.roads) >= len(a.structures) - 1
    assert any(s["type"] in {"castle", "town_hall"} for s in a.structures)
    assert any(s["type"] == "market" for s in a.landmarks)
