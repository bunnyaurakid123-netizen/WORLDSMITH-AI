from worldsmith.memory import MemoryStore


def test_memory_round_trip(tmp_path):
    store = MemoryStore(tmp_path / "memory.db")
    memory_id = store.remember("Prefer dramatic mountains and spruce architecture.", "preference")
    assert memory_id > 0
    found = store.search("dramatic mountains")
    assert found and found[0].id == memory_id


def test_conversation_context(tmp_path):
    store = MemoryStore(tmp_path / "memory.db")
    store.remember("Keep the main castle on a cliff.")
    store.save_conversation("C:/world", "Build a castle", "Castle generated with cliff placement")
    context = store.build_context("castle cliff", "C:/world")
    assert "castle" in context.lower()
    assert "cliff" in context.lower()
