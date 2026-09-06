from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QFileDialog, QMessageBox

from worldsmith.project import WorldSmithProject


def install_project_menu(window) -> None:
    menu = window.menuBar().addMenu("Project")
    save_action = menu.addAction("Save Project…")
    load_action = menu.addAction("Load Project…")
    menu.addSeparator()
    export_action = menu.addAction("Export Plan JSON…")

    save_action.triggered.connect(lambda: save_project(window))
    load_action.triggered.connect(lambda: load_project(window))
    export_action.triggered.connect(lambda: export_plan(window))


def _camera_state(window) -> dict[str, float]:
    preview = getattr(window, "live_preview", None)
    if preview is None:
        return {}
    return {
        "yaw": float(getattr(preview, "yaw", 0.0)),
        "pitch": float(getattr(preview, "pitch", 0.0)),
        "zoom": float(getattr(preview, "zoom", 1.0)),
        "pan_x": float(getattr(preview, "pan_x", 0.0)),
        "pan_y": float(getattr(preview, "pan_y", 0.0)),
    }


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
    project.metadata = {
        "world_name": window.current.name,
        "worldsmith": "0.3.0",
    }
    project.save(Path(path))
    window.statusBar().showMessage(f"Project saved: {path}")


def load_project(window) -> None:
    path, _ = QFileDialog.getOpenFileName(window, "Load WorldSmith Project", "", "WorldSmith Project (*.worldsmith.json)")
    if not path:
        return
    try:
        project = WorldSmithProject.load(Path(path))
        project_world = Path(project.world_path)
        if not project_world.is_dir():
            raise ValueError(f"Project world does not exist: {project_world}")

        matches = [item for item in window._saves if item.path.resolve() == project_world.resolve()]
        if matches:
            for index in range(window.save_list.count()):
                item = window.save_list.item(index)
                if item.data(window.save_list.UserRole).path.resolve() == project_world.resolve():
                    window.save_list.setCurrentItem(item)
                    break
        else:
            QMessageBox.warning(window, "WorldSmith Project", "The project world is not in the current save scan. Use Choose saves folder, then load the project again.")
            return

        window.open_selected()
        window.request.setPlainText(project.prompt)
        window.last_plan = dict(project.plan)
        if window.last_plan:
            window.plan_output.setPlainText(window.planner_output(window.last_plan) if hasattr(window, "planner_output") else __import__("json").dumps(window.last_plan, indent=2))
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


def export_plan(window) -> None:
    if not window.last_plan:
        QMessageBox.information(window, "WorldSmith Project", "Generate a plan first.")
        return
    path, _ = QFileDialog.getSaveFileName(window, "Export Plan JSON", "worldsmith-plan.json", "JSON (*.json)")
    if not path:
        return
    Path(path).write_text(__import__("json").dumps(window.last_plan, indent=2), encoding="utf-8")
    window.statusBar().showMessage(f"Plan exported: {path}")
