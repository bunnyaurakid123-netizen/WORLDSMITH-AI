from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QThread, Signal

from worldsmith.backup import backup_world
from worldsmith.world import WorldEditor
import worldsmith.app as app_module


class BuildWorker(QObject):
    finished = Signal(object)
    failed = Signal(str)
    activity = Signal(str)

    def __init__(self, world_path: Path, plan: dict, auto_backup: bool):
        super().__init__()
        self.world_path = Path(world_path)
        self.plan = plan
        self.auto_backup = bool(auto_backup)

    def run(self):
        editor = None
        try:
            backup = None
            if self.auto_backup:
                self.activity.emit("Backup • creating safety snapshot")
                backup = backup_world(self.world_path)
            self.activity.emit("World I/O • opening Minecraft save")
            editor = WorldEditor(self.world_path)
            summary = editor.open()
            self.activity.emit(f"World I/O • opened {summary.path.name}")
            builder_class = app_module.WorldBuilder
            self.activity.emit(f"Generator • running {builder_class.__name__}")
            result = builder_class(editor.require_level(), seed=int(self.plan.get("seed", 1337))).build(self.plan)
            self.activity.emit("World I/O • saving generated changes")
            editor.save()
            editor.close()
            editor = None
            self.activity.emit("Generator • build complete")
            self.finished.emit({"result": result, "backup": backup})
        except Exception as exc:
            if editor is not None:
                try:
                    editor.close()
                except Exception:
                    pass
            self.failed.emit(str(exc))


def build_plan_async(window) -> None:
    if not window.current or not window.last_plan:
        return
    if getattr(window, "_build_thread", None) is not None and window._build_thread.isRunning():
        window.statusBar().showMessage("A build is already running")
        return

    # Never keep the main Amulet handle open while the worker edits the same save.
    window.close_editor()
    window.save_settings()
    window.build_button.setEnabled(False)
    window.plan_btn.setEnabled(False)
    window.progress.setRange(0, 0)
    window.progress.show()
    window.activity.appendPlainText("WorldSmith • starting background build")

    thread = QThread(window)
    worker = BuildWorker(window.current.path, window.last_plan, window.settings.auto_backup)
    worker.moveToThread(thread)
    thread.started.connect(worker.run)
    worker.activity.connect(window.activity.appendPlainText)
    worker.finished.connect(lambda payload: _build_finished(window, payload))
    worker.failed.connect(lambda message: _build_failed(window, message))
    worker.finished.connect(thread.quit)
    worker.failed.connect(thread.quit)
    thread.finished.connect(worker.deleteLater)
    thread.finished.connect(thread.deleteLater)
    thread.finished.connect(lambda: _build_cleanup(window))
    window._build_thread = thread
    window._build_worker = worker
    thread.start()


def _build_finished(window, payload):
    result = payload["result"]
    backup = payload.get("backup")
    message = (
        f"Built {result.blocks_changed:,} blocks • "
        f"{result.structures_changed:,} structures • "
        f"{result.interiors_changed:,} interior blocks • "
        f"{result.systems_changed:,} redstone blocks"
    )
    if backup:
        message += f" • backup: {backup}"
    window.activity.appendPlainText("WorldSmith • " + message)
    window.statusBar().showMessage(message)
    window.build_button.setEnabled(False)
    # Reopen the saved world so the inspector and live voxel preview reflect the result.
    try:
        window.open_selected()
    except Exception as exc:
        window.activity.appendPlainText(f"WorldSmith • refresh after build failed: {exc}")


def _build_failed(window, message: str):
    window.activity.appendPlainText(f"WorldSmith • BUILD ERROR: {message}")
    from PySide6.QtWidgets import QMessageBox
    QMessageBox.critical(window, "WorldSmith build", message)


def _build_cleanup(window):
    window.progress.hide()
    window.plan_btn.setEnabled(True)
    window._build_thread = None
    window._build_worker = None
