from worldsmith.generation.builder import WorldBuilder


def make_builder(seed=1337):
    builder = WorldBuilder.__new__(WorldBuilder)
    builder.seed = seed
    return builder


def test_height_field_is_deterministic():
    a = make_builder(42)
    b = make_builder(42)
    samples_a = [a.height_at(x, z, 100, 80, 1.0) for x, z in [(0, 0), (12, 34), (-41, 19), (80, -25)]]
    samples_b = [b.height_at(x, z, 100, 80, 1.0) for x, z in [(0, 0), (12, 34), (-41, 19), (80, -25)]]
    assert samples_a == samples_b


def test_different_seeds_change_terrain():
    a = make_builder(1)
    b = make_builder(999)
    values_a = [a.height_at(x, z, 100, 80, 1.0) for x, z in [(10, 10), (20, 30), (-15, 60)]]
    values_b = [b.height_at(x, z, 100, 80, 1.0) for x, z in [(10, 10), (20, 30), (-15, 60)]]
    assert values_a != values_b
