from types import SimpleNamespace

from worldsmith.generation.production_builder import ProductionWorldBuilder


class FakeLevel:
    def __init__(self, block_name):
        self.block_name = block_name
        self.writes = []

    def all_chunk_coords(self, _dimension):
        return {(0, 0)}

    def get_version_block(self, *_args):
        return SimpleNamespace(namespaced_name=self.block_name), None

    def set_version_block(self, *args, **_kwargs):
        self.writes.append(args)


def _builder(fake):
    builder = object.__new__(ProductionWorldBuilder)
    builder._raw_level = fake
    builder._existing_chunks = {(0, 0)}
    builder._preserve_existing = True
    builder._allow_terrain_regeneration = False
    builder._max_blocks = 2
    builder._write_count = 0
    builder._skipped_count = 0
    builder._phase = "structures"
    return builder


def test_natural_ground_can_be_replaced():
    fake = FakeLevel("minecraft:dirt")
    builder = _builder(fake)
    assert builder._guarded_write(1, 64, 1, "minecraft:overworld", ("java", (1, 21, 0)), "new-block")
    assert len(fake.writes) == 1


def test_player_block_is_protected():
    fake = FakeLevel("minecraft:chest")
    builder = _builder(fake)
    assert not builder._guarded_write(1, 64, 1, "minecraft:overworld", ("java", (1, 21, 0)), "new-block")
    assert not fake.writes


def test_block_budget_is_hard():
    fake = FakeLevel("minecraft:air")
    builder = _builder(fake)
    assert builder._guarded_write(1, 64, 1, "minecraft:overworld", ("java", (1, 21, 0)), "a")
    assert builder._guarded_write(2, 64, 1, "minecraft:overworld", ("java", (1, 21, 0)), "b")
    assert not builder._guarded_write(3, 64, 1, "minecraft:overworld", ("java", (1, 21, 0)), "c")
    assert builder._write_count == 2
