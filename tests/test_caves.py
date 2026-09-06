from worldsmith.generation.caves import _fbm3, _noise3


def test_noise3_is_bounded():
    for point in ((0, 0, 0), (1, 2, 3), (-4, 7, 11)):
        value = _noise3(*point, 42)
        assert 0.0 <= value <= 1.0


def test_fbm3_is_bounded_and_deterministic():
    first = _fbm3(0.7, 1.2, -3.4, 99)
    second = _fbm3(0.7, 1.2, -3.4, 99)
    assert 0.0 <= first <= 1.0
    assert first == second
