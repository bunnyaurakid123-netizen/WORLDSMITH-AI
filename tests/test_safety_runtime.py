from worldsmith.generation.safety import is_air, is_natural_replaceable
from worldsmith.memory import MemoryStore


def test_block_classification():
    assert is_air("minecraft:air")
    assert is_air("minecraft:cave_air")
    assert is_natural_replaceable("minecraft:dirt")
    assert is_natural_replaceable("minecraft:stone")
    assert not is_natural_replaceable("minecraft:chest")
    assert not is_natural_replaceable("minecraft:glass")
    assert not is_natural_replaceable("minecraft:redstone_wire")


def test_outcome_memory_is_recalled(tmp_path):
    store = MemoryStore(tmp_path / "memory.db")
    store.save_outcome("C:/world", "Build a mountain castle", "verified", 72.5, "Keep the castle on the western ridge")
    context = store.build_context("mountain castle western ridge", "C:/world")
    assert "western ridge" in context
    assert "72.5" in context
