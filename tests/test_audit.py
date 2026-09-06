import json

from worldsmith.audit import BuildAudit


def test_build_audit_round_trip(tmp_path):
    audit = BuildAudit.start(tmp_path / "World", {"seed": 42, "summary": "test", "_ensemble": ["ollama"], "_judge": "ollama"})
    audit.elapsed_seconds = 1.25
    audit.blocks_changed = 123
    path = audit.save(tmp_path / "runs")
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["seed"] == 42
    assert data["blocks_changed"] == 123
    assert data["providers"] == ["ollama"]
