import pytest

from worldsmith.generation.primitive_ops import PrimitiveOperationCompiler


def test_operation_limit_without_loading_amulet():
    class FakeLevel:
        pass

    compiler = PrimitiveOperationCompiler(FakeLevel())
    with pytest.raises(ValueError, match="Too many primitive operations"):
        compiler.apply([{"op": "sphere", "x": 0, "y": 0, "z": 0, "radius": 2}] * 49)


def test_block_budget_without_loading_amulet():
    class FakeLevel:
        pass

    compiler = PrimitiveOperationCompiler(FakeLevel())
    huge = {"op": "fill_box", "x1": 0, "y1": 0, "z1": 0, "x2": 100, "y2": 100, "z2": 100, "block": "stone"}
    with pytest.raises(ValueError, match="Primitive edit budget exceeded"):
        compiler.apply([huge])
