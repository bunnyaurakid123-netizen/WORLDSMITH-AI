from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFileDialog, QMessageBox, QInputDialog

from worldsmith.backup import list_backups, restore_world
from worldsmith.project import WorldSmithProject


def install_project_menu(window) -> None:
    menu = window.menuBar().addMenu("Project")
    save_action = menu.addAction("Save Project…")
    load_action = menu.addAction("Load Project…")
    menu.addSeparator()
    export_action = menu.addAction("Export Plan JSON…")
    repair_action = menu.addAction("Load Latest AI Repair Proposal")
    repair_action.setEnabled(False)
    restore_action = menu.addAction("Restore World Snapshot…")
    window._repair_action = repair_action
    window._restore_action = restore_action
    save_action.triggered.connect(lambda: save_project(window))
    load_action.triggered.connect(lambda: load_project(window))
    export_action.triggered.connect(lambda: export_plan(window))
    repair_action.triggered.connect(lambda: load_repair_proposal(window))
    restore_action.triggered.connect(lambda: restore_snapshot(window))


def _camera_state(window) -> dict[str, float]:
    preview = getattr(window, "live_preview", None)
    if preview is None:
        return {}
    return {key: float(getattr(preview, key, default)) for key, default in (("yaw", 0.0), ("pitch", 0.0), ("zoom", 1.0), ("pan_x", 0.0), ("pan_y", 0.0))}


def save_project(window) -> None:
    if not window.current:
        QMessageBox.information(window, "WorldSmith Project", "Open a world first.")
        return
    path, _ = QFileDialog.getSaveFileName(window, "Save WorldSmith Project", "", "WorldSmith Project (*.worldsmith.json)")
    if not path:
        return
    project = WorldSmithProject.new(window.current.path)
    project.prompt = window.request.toPlainText()
    project.plan = dict(window.last_plan or {})
    project.camera = _camera_state(window)
    project.metadata = {"world_name": window.current.name, "worldsmith": "0.4.0"}
    project.save(Path(path))
    window.statusBar().showMessage(f"Project saved: {path}")


def load_project(window) -> None:
    path, _ = QFileDialog.getOpenFileName(window, "Load WorldSmith Project", "", "WorldSmith Project (*.worldsmith.json)")
    if not path:
        return
    try:
        project = WorldSmithProject.load(Path(path))
        project_world = Path(project.world_path).resolve()
        matching_index = None
        for index in range(window.save_list.count()):
            item = window.save_list.item(index)
            save = item.data(Qt.UserRole)
            if save and save.path.resolve() == project_world:
                matching_index = index
                break
        if matching_index is None:
            QMessageBox.warning(window, "WorldSmith Project", "The project world is not in the current save scan. Scan or choose the saves folder containing it, then load the project again.")
            return
        window.save_list.setCurrentRow(matching_index)
        window.open_selected()
        window.request.setPlainText(project.prompt)
        window.last_plan = dict(project.plan)
        if window.last_plan:
            window.plan_output.setPlainText(json.dumps(window.last_plan, indent=2))
        preview = getattr(window, "live_preview", None)
        if preview:
            for key, value in project.camera.items():
                if hasattr(preview, key):
                    setattr(preview, key, float(value))
            preview.update()
        window.build_button.setEnabled(bool(window.last_plan.get("builds")) if window.last_plan else False)
        window.statusBar().showMessage(f"Project loaded: {path}")
    except Exception as exc:
        QMessageBox.critical(window, "WorldSmith Project", str(exc))


def set_repair_proposal(window, path: str | None):
    window.last_repair_plan_path = Path(path) if path else None
    action = getattr(window, "_repair_action", None)
    if action:
        action.setEnabled(bool(window.last_repair_plan_path and window.last_repair_plan_path.exists()))


def load_repair_proposal(window) -> None:
    path = getattr(window, "last_repair_plan_path", None)
    if path is None or not Path(path).exists():
        QMessageBox.information(window, "AI Repair", "No repair proposal is available yet.")
        return
    try:
        plan = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(plan, dict):
            raise ValueError("Repair proposal is not a JSON object")
        window.last_plan = plan
        window.plan_output.setPlainText(json.dumps(plan, indent=2))
        window.build_button.setEnabled(bool(plan.get("builds") or plan.get("operations")))
        window.request.setPlainText(f"AI repair proposal loaded from {Path(path).name}. Review it before building.")
        window.statusBar().showMessage("AI repair proposal loaded; review before Build")
        try:
            window._switch_page(1)
        except Exception:
            pass
    except Exception as exc:
        QMessageBox.critical(window, "AI Repair", str(exc))


def restore_snapshot(window) -> None:
    if not window.current:
        QMessageBox.information(window, "Restore Snapshot", "Open a world first.")
        return
    backups = list_backups(window.current.path)
    if not backups:
        QMessageBox.information(window, "Restore Snapshot", "No snapshots were found for this world.")
        return
    labels = [f"{path.name} ({datetime_text(path)})" for path in backups[:30]]
    choice, accepted = QInputDialog.getItem(window, "Restore World Snapshot", "Choose a snapshot:", labels, 0, False)
    if not accepted:
        return
    index = labels.index(choice)
    selected = backups[index]
    confirm = QMessageBox.question(window, "Confirm restore", f"Restore {window.current.name} from:\n\n{selected}\n\nThe current world will be replaced by this snapshot.", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
    if confirm != QMessageBox.Yes:
        return
    try:
        window.close_editor()
        restore_world(window.current.path, selected, confirm=True)
        window.open_selected()
        window.statusBar().showMessage(f"World restored from {selected.name}")
    except Exception as exc:
        QMessageBox.critical(window, "Restore Snapshot", str(exc))


def datetime_text(path: Path) -> str:
    try:
        from datetime import datetime
        return datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
    except OSError:
        return "unknown time"


def export_plan(window) -> None:
    if not window.last_plan:
        QMessageBox.information(window, "WorldSmith Project", "Generate a plan first.")
        return
    path, _ = QFileDialog.getSaveFileName(window, "Export Plan JSON", "worldsmith-plan.json", "JSON (*.json)")
    if not path:
        return
    Path(path).write_text(json.dumps(window.last_plan, indent=2), encoding="utf-8")
    window.statusBar().showMessage(f"Plan exported: {path}")
