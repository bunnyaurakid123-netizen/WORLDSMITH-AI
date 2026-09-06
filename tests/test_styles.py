from worldsmith.generation.styles import resolve_style


def test_style_resolution():
    medieval = resolve_style("grand medieval kingdom")
    modern = resolve_style("modern city")
    desert = resolve_style("desert palace")
    assert "stone" in medieval.wall
    assert "quartz" in modern.wall
    assert "sandstone" in desert.wall


def test_unknown_style_has_safe_default():
    assert resolve_style("totally-unknown-style").wall == resolve_style("medieval").wall
