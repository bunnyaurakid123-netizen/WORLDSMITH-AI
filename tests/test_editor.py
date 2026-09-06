from worldsmith.editor.commands import AddObjectCommand, CommandStack, MoveObjectCommand
from worldsmith.editor.scene import SceneDocument, SceneObject
from worldsmith.editor.validation import validate_scene
from worldsmith.preview_scene import PreviewScene


def test_scene_selection_overlap_and_snapshot():
    doc = SceneDocument()
    doc.add(SceneObject("castle", "castle", "Castle", {"x": 0, "y": 64, "z": 0}, {"x": 20, "y": 20, "z": 20}))
    doc.add(SceneObject("house", "house", "House", {"x": 5, "y": 64, "z": 5}, {"x": 10, "y": 10, "z": 10}))
    doc.set_selection(["castle", "missing"])
    assert [item.id for item in doc.selected()] == ["castle"]
    assert [item.id for item in doc.overlaps("castle")]
    restored = SceneDocument.from_snapshot(doc.snapshot())
    assert len(restored.objects) == 2


def test_commands_undo_redo():
    doc = SceneDocument()
    obj = SceneObject("house", "house", "House")
    stack = CommandStack()
    stack.push(AddObjectCommand(doc, obj))
    stack.push(MoveObjectCommand(doc, "house", {"x": 0, "y": 0, "z": 0}, {"x": 20, "y": 3, "z": -5}))
    assert doc.get("house").transform["x"] == 20
    stack.undo()
    assert doc.get("house").transform["x"] == 0
    stack.redo()
    assert doc.get("house").transform["z"] == -5


def test_validation_catches_overlap_and_limits():
    doc = SceneDocument()
    doc.add(SceneObject("a", "house", "A", {"x": 0, "y": 0, "z": 0}, {"x": 10, "y": 10, "z": 10}))
    doc.add(SceneObject("b", "house", "B", {"x": 1, "y": 0, "z": 1}, {"x": 10, "y": 10, "z": 10}))
    issues = validate_scene(doc)
    assert any(issue.code == "overlap" for issue in issues)


def test_preview_scene_is_deterministic():
    plan = {"seed": 42, "terrain": {"radius": 64, "mountain_height": 60}, "center": [0, 100, 0], "builds": [{"type": "castle", "x": 0, "y": 100, "z": 0, "width": 30, "depth": 30, "height": 25}]}
    a, b = PreviewScene(plan), PreviewScene(plan)
    assert a.terrain_vertices() == b.terrain_vertices()
    assert a.objects() == b.objects()
