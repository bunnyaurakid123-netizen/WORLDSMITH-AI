import json

from worldsmith.project import WorldSmithProject


def test_project_round_trip(tmp_path):
    project = WorldSmithProject.new(tmp_path / "World")
    project.prompt = "build a castle"
    project.plan = {"seed": 99, "builds": []}
    project.camera = {"yaw": 10.0, "zoom": 1.5}
    path = project.save(tmp_path / "demo.worldsmith.json")

    loaded = WorldSmithProject.load(path)
    assert loaded.world_path == str(tmp_path / "World")
    assert loaded.prompt == "build a castle"
    assert loaded.plan["seed"] == 99
    assert loaded.camera["zoom"] == 1.5


def test_project_file_is_json(tmp_path):
    path = WorldSmithProject.new().save(tmp_path / "demo.worldsmith.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["format_version"] == 1
