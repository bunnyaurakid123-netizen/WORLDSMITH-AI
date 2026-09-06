from worldsmith.editor.brushes import cylinder, fill_box, hollow_box, sphere
from worldsmith.editor.operations import Selection
from worldsmith.editor.transactions import BlockState, EditHistory, EditTransaction


class FakeAdapter:
    def __init__(self):
        self.blocks = {}

    def get_block(self, x, y, z):
        return self.blocks.get((x, y, z), BlockState("air"))

    def set_block(self, x, y, z, state):
        self.blocks[(x, y, z)] = state


def test_transaction_undo_redo():
    adapter = FakeAdapter()
    history = EditHistory(adapter)
    tx = EditTransaction(adapter)
    tx.record(1, 2, 3, BlockState("stone"))
    assert history.commit(tx) == 1
    assert adapter.blocks[(1, 2, 3)].block == "stone"
    assert history.undo() == 1
    assert adapter.blocks[(1, 2, 3)].block == "air"
    assert history.redo() == 1
    assert adapter.blocks[(1, 2, 3)].block == "stone"


def test_fill_and_hollow_bounds():
    adapter = FakeAdapter()
    tx = EditTransaction(adapter)
    result = fill_box(tx, 0, 0, 0, 2, 1, 2, BlockState("stone"))
    assert result.changed == 18
    assert result.bounds == (0, 0, 0, 2, 1, 2)

    adapter = FakeAdapter()
    tx = EditTransaction(adapter)
    result = hollow_box(tx, 0, 0, 0, 2, 2, 2, BlockState("stone"))
    assert result.changed == 26


def test_sphere_and_cylinder_are_nonempty():
    adapter = FakeAdapter()
    tx = EditTransaction(adapter)
    assert sphere(tx, 0, 0, 0, 2, BlockState("stone")).changed > 0
    adapter = FakeAdapter()
    tx = EditTransaction(adapter)
    assert cylinder(tx, 0, 0, 0, 2, 4, BlockState("stone")).changed > 0


def test_selection_normalization_and_volume():
    selection = Selection(5, 9, 3, 1, 4, 0).normalized
    assert selection == Selection(1, 4, 0, 5, 9, 3)
    assert selection.volume == 120
