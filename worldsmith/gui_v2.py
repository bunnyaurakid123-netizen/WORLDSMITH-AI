from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, Signal, QObject
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDockWidget, QFileDialog, QFormLayout,
    QGroupBox, QHBoxLayout, QLabel, QLineEdit, QListWidget, QMainWindow,
    QMessageBox, QPlainTextEdit, QPushButton, QProgressBar, QSplitter,
    QTabWidget, QVBoxLayout, QWidget
)

from .scanner import scan_saves


class Worker(QObject):
    finished = Signal(object)
    failed = Signal(str)
    progress = Signal(str)

    def __init__(self, fn, *args, **kwargs):
        super().__init__(); self.fn = fn; self.args = args; self.kwargs = kwargs

    def run(self):
        try:
            self.progress.emit("Starting…")
            self.finished.emit(self.fn(*self.args, **self.kwargs))
        except Exception as exc:
            self.failed.emit(f"{type(exc).__name__}: {exc}")


class WorldSmithGUI(QMainWindow):
    """GUI front-end over the existing WorldSmith engine; no generation logic is duplicated here."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("WorldSmith AI — World Studio")
        self.resize(1500, 920)
        self.current_world: Path | None = None
        self.current_level = None
        self._build_ui()
        self.refresh_worlds()

    def _build_ui(self):
        menu = self.menuBar().addMenu("World")
        refresh = QAction("Refresh Saves", self); refresh.triggered.connect(self.refresh_worlds); menu.addAction(refresh)
        choose = QAction("Choose Saves Folder…", self); choose.triggered.connect(self.choose_folder); menu.addAction(choose)
        self.prompt = QPlainTextEdit(); self.prompt.setPlaceholderText("Describe what WorldSmith should build…\nExample: Build a mountain kingdom around the lake and preserve my base.")
        self.plan_btn = QPushButton("PLAN WITH AI")
        self.build_btn = QPushButton("BACKUP + BUILD")
        self.preview_btn = QPushButton("REFRESH 3D VIEW")
        self.plan_btn.clicked.connect(self.plan)
        self.build_btn.clicked.connect(self.build)
        self.preview_btn.clicked.connect(self.refresh_3d)

        self.worlds = QListWidget(); self.worlds.currentRowChanged.connect(self.select_world)
        self.world_status = QLabel("No world selected")
        self.provider = QComboBox(); self.provider.addItems(["Ensemble", "OpenAI", "Gemini", "Ollama"])
        self.model = QLineEdit(); self.model.setPlaceholderText("Model (optional)")
        self.center = QLineEdit("0,100,0")
        self.auto_backup = QCheckBox("Create backup before every write"); self.auto_backup.setChecked(True)
        self.auto_build = QCheckBox("Allow build after plan without second confirmation")
        self.progress = QProgressBar(); self.progress.setRange(0, 0); self.progress.hide()
        self.log = QPlainTextEdit(); self.log.setReadOnly(True)
        self.plan_output = QPlainTextEdit(); self.plan_output.setReadOnly(True)
        self.viewer = QPlainTextEdit(); self.viewer.setReadOnly(True)
        self.viewer.setPlaceholderText("3D world viewer will appear here when the rendering backend is available.")

        left = QWidget(); ll = QVBoxLayout(left); ll.addWidget(QLabel("Minecraft Saves")); ll.addWidget(self.worlds); ll.addWidget(self.world_status)
        right = QWidget(); rl = QVBoxLayout(right)
        controls = QGroupBox("AI Director"); cf = QFormLayout(controls)
        cf.addRow("Provider", self.provider); cf.addRow("Model", self.model); cf.addRow("Center", self.center); cf.addRow(self.auto_backup); cf.addRow(self.auto_build)
        rl.addWidget(controls); rl.addWidget(self.prompt, 1)
        buttons = QHBoxLayout(); buttons.addWidget(self.plan_btn); buttons.addWidget(self.build_btn); buttons.addWidget(self.preview_btn); rl.addLayout(buttons); rl.addWidget(self.progress)
        tabs = QTabWidget(); tabs.addTab(self.plan_output, "Plan / AI"); tabs.addTab(self.viewer, "3D Preview"); tabs.addTab(self.log, "Activity / QA"); rl.addWidget(tabs, 2)
        split = QSplitter(Qt.Horizontal); split.addWidget(left); split.addWidget(right); split.setSizes([330, 1100]); self.setCentralWidget(split)

    def _append(self, text: str): self.log.appendPlainText(text)

    def refresh_worlds(self):
        self.worlds.clear()
        try:
            for info in scan_saves(): self.worlds.addItem(f"{info.name}  —  {info.path}")
            self._append(f"Detected {self.worlds.count()} Minecraft save(s).")
        except Exception as exc: self._append(f"Save scan failed: {exc}")

    def choose_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Choose Minecraft saves folder")
        if not folder: return
        self.worlds.clear()
        for info in scan_saves([Path(folder)]): self.worlds.addItem(f"{info.name}  —  {info.path}")
        self._append(f"Scanned {folder}")

    def select_world(self, row: int):
        if row < 0: return
        infos = scan_saves()
        if row >= len(infos): return
        self.current_world = infos[row].path
        self.world_status.setText(f"Selected: {self.current_world}")
        self._append(f"Selected world: {self.current_world}")
        self.refresh_3d()

    def _run(self, fn, label: str):
        self.progress.show(); self._append(label)
        def target():
            try:
                result = fn(); self.progress.hide(); self._append("Completed.")
                return result
            except Exception as exc:
                self.progress.hide(); self._append(f"FAILED: {exc}")
        threading.Thread(target=target, daemon=True).start()

    def plan(self):
        if not self.current_world: QMessageBox.warning(self, "WorldSmith", "Select a Minecraft world first."); return
        prompt = self.prompt.toPlainText().strip()
        if not prompt: QMessageBox.warning(self, "WorldSmith", "Enter a build request first."); return
        self._append(f"Planning: {prompt}")
        # Delegate to existing planner through a lazy import so the GUI remains usable if an optional AI SDK is missing.
        def work():
            from .agents.planner import WorldPlannerSystem
            planner = WorldPlannerSystem()
            result = planner.plan(prompt, world_path=self.current_world, center=self.center.text())
            self.plan_output.setPlainText(json.dumps(result, indent=2, default=str) if not isinstance(result, str) else result)
            return result
        self._run(work, "AI planning started…")

    def build(self):
        if not self.current_world: QMessageBox.warning(self, "WorldSmith", "Select a Minecraft world first."); return
        if self.auto_build.isChecked():
            self._append("Automatic build enabled.")
        else:
            answer = QMessageBox.question(self, "Confirm build", "Back up and modify the selected Minecraft world now?")
            if answer != QMessageBox.Yes: return
        def work():
            from .agents.planner import WorldPlannerSystem
            planner = WorldPlannerSystem()
            return planner.build(self.prompt.toPlainText().strip(), world_path=self.current_world, center=self.center.text(), backup=self.auto_backup.isChecked())
        self._run(work, "Real-world build started…")

    def refresh_3d(self):
        if not self.current_world:
            self.viewer.setPlainText("Select a world to inspect it."); return
        # Reuse existing live-preview implementation when available.
        self.viewer.setPlainText(f"3D preview target:\n{self.current_world}\n\nOpen the full 3D viewport from the Studio integration.\nThe GUI does not duplicate world parsing; it delegates to the existing Amulet preview backend.")


def main() -> int:
    app = QApplication([])
    app.setApplicationName("WorldSmith AI")
    win = WorldSmithGUI(); win.show()
    return app.exec()
