from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal, QObject
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from worldsmith.ai.orchestrator import Ensemble
from worldsmith.backup import backup_world
from worldsmith.config import Settings
from worldsmith.context import inspect_world
from worldsmith.generation.builder import WorldBuilder
from worldsmith.planner import Planner
from worldsmith.scanner import scan_saves
from worldsmith.world import WorldEditor


APP_STYLE = """
QMainWindow, QWidget {
    background: #0b1020;
    color: #e8ecf7;
    font-family: "Segoe UI";
    font-size: 13px;
}
QFrame#sidebar {
    background: #080d19;
    border-right: 1px solid #202943;
}
QFrame#topbar, QFrame#card {
    background: #11182b;
    border: 1px solid #202943;
    border-radius: 14px;
}
QFrame#hero {
    background: #111a31;
    border: 1px solid #27365d;
    border-radius: 18px;
}
QLabel#brand {
    font-size: 21px;
    font-weight: 700;
}
QLabel#muted {
    color: #8d98b3;
}
QLabel#title {
    font-size: 25px;
    font-weight: 700;
}
QLabel#section {
    font-size: 15px;
    font-weight: 650;
}
QLabel#metric {
    font-size: 26px;
    font-weight: 700;
}
QPushButton {
    background: #17213a;
    color: #eef2ff;
    border: 1px solid #2c3856;
    border-radius: 9px;
    padding: 9px 14px;
}
QPushButton:hover {
    background: #1c2946;
    border-color: #536da8;
}
QPushButton:pressed {
    background: #10182b;
}
QPushButton#primary {
    background: #4f67ff;
    border-color: #6478ff;
    font-weight: 650;
}
QPushButton#primary:hover {
    background: #6076ff;
}
QPushButton#nav {
    text-align: left;
    padding: 11px 13px;
    background: transparent;
    border: 0;
    color: #aab4cb;
}
QPushButton#nav:hover {
    background: #121b30;
    color: #ffffff;
}
QPushButton#nav:checked {
    background: #182448;
    color: #ffffff;
    border-left: 3px solid #6a7dff;
}
QLineEdit, QPlainTextEdit, QListWidget, QSpinBox {
    background: #0b1222;
    color: #e8ecf7;
    border: 1px solid #27324b;
    border-radius: 9px;
    padding: 8px;
}
QPlainTextEdit {
    padding: 11px;
}
QListWidget::item {
    padding: 10px;
    margin: 3px 0;
    border-radius: 8px;
}
QListWidget::item:selected {
    background: #1a2850;
    border: 1px solid #3c5287;
}
QProgressBar {
    background: #0a1120;
    border: 1px solid #26324b;
    border-radius: 7px;
    text-align: center;
    height: 13px;
}
QProgressBar::chunk {
    background: #6077ff;
    border-radius: 7px;
}
QCheckBox {
    spacing: 8px;
}
"""


class Card(QFrame):
    def __init__(self, title: str | None = None):
        super().__init__()
        self.setObjectName("card")
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(16, 16, 16, 16)
        self.layout.setSpacing(10)
        if title:
            label = QLabel(title)
            label.setObjectName("section")
            self.layout.addWidget(label)


class PlannerWorker(QObject):
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, planner: Planner, request: str, context: str, center: tuple[int, int, int]):
        super().__init__()
        self.planner = planner
        self.request = request
        self.context = context
        self.center = center

    def run(self):
        try:
            self.finished.emit(self.planner.make_plan(self.request, self.context, self.center))
        except Exception as exc:
            self.failed.emit(str(exc))


class WorldSmithWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("WorldSmith AI")
        self.resize(1440, 900)
        self.setMinimumSize(1100, 720)

        self.settings_path = Path.home() / ".worldsmith" / "settings.json"
        self.settings = Settings.load(self.settings_path)
        self.settings.apply_env()
        self.current = None
        self.editor = None
        self.last_plan = None
        self._saves = []
        self._thread = None
        self._worker = None

        self._build_ui()
        self.refresh_saves()
        self._refresh_provider_status()

    def _build_ui(self):
        self.setStyleSheet(APP_STYLE)
        root = QWidget()
        outer = QHBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(220)
        sl = QVBoxLayout(sidebar)
        sl.setContentsMargins(16, 20, 16, 16)

        brand = QLabel("WORLDsmith")
        brand.setObjectName("brand")
        sl.addWidget(brand)
        subtitle = QLabel("Minecraft world architect")
        subtitle.setObjectName("muted")
        sl.addWidget(subtitle)
        sl.addSpacing(22)

        self.nav_buttons = []
        for label, index in [("Overview", 0), ("AI Builder", 1), ("World Inspector", 2), ("Settings", 3)]:
            button = QPushButton(label)
            button.setObjectName("nav")
            button.setCheckable(True)
            button.clicked.connect(lambda checked, i=index: self._switch_page(i))
            sl.addWidget(button)
            self.nav_buttons.append(button)
        self.nav_buttons[0].setChecked(True)
        sl.addStretch()
        self.sidebar_status = QLabel("Ready")
        self.sidebar_status.setObjectName("muted")
        sl.addWidget(self.sidebar_status)
        outer.addWidget(sidebar)

        content = QWidget()
        main = QVBoxLayout(content)
        main.setContentsMargins(18, 18, 18, 18)
        main.setSpacing(14)

        topbar = QFrame()
        topbar.setObjectName("topbar")
        tl = QHBoxLayout(topbar)
        tl.setContentsMargins(16, 11, 16, 11)
        self.page_title = QLabel("Overview")
        self.page_title.setObjectName("section")
        tl.addWidget(self.page_title)
        tl.addStretch()
        self.active_world_chip = QLabel("No world selected")
        self.active_world_chip.setObjectName("muted")
        tl.addWidget(self.active_world_chip)
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh_saves)
        tl.addWidget(refresh_btn)
        main.addWidget(topbar)

        self.pages = QStackedWidget()
        self.pages.addWidget(self._overview_page())
        self.pages.addWidget(self._builder_page())
        self.pages.addWidget(self._inspector_page())
        self.pages.addWidget(self._settings_page())
        main.addWidget(self.pages, 1)
        outer.addWidget(content, 1)
        self.setCentralWidget(root)
        self.statusBar().showMessage("WorldSmith ready")

    def _overview_page(self):
        page = QWidget()
        root = QVBoxLayout(page)
        root.setContentsMargins(4, 4, 4, 4)
        root.setSpacing(14)

        hero = QFrame()
        hero.setObjectName("hero")
        hl = QVBoxLayout(hero)
        hl.setContentsMargins(24, 22, 24, 22)
        title = QLabel("Build worlds with intent.")
        title.setObjectName("title")
        hl.addWidget(title)
        body = QLabel(
            "Describe mountains, castles, villages, interiors and redstone systems. "
            "WorldSmith plans the build with multiple AI providers and writes it into a real save."
        )
        body.setWordWrap(True)
        body.setObjectName("muted")
        hl.addWidget(body)
        actions = QHBoxLayout()
        open_btn = QPushButton("Open selected world")
        open_btn.setObjectName("primary")
        open_btn.clicked.connect(self.open_selected)
        actions.addWidget(open_btn)
        choose_btn = QPushButton("Choose saves folder")
        choose_btn.clicked.connect(self.choose_folder)
        actions.addWidget(choose_btn)
        actions.addStretch()
        hl.addLayout(actions)
        root.addWidget(hero)

        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(14)
        for col in range(3):
            grid.setColumnStretch(col, 1)

        saves_card = Card("Minecraft saves")
        row = QHBoxLayout()
        self.overview_saves = QLabel("0")
        self.overview_saves.setObjectName("metric")
        row.addWidget(self.overview_saves)
        row.addStretch()
        row.addWidget(QLabel("detected"))
        saves_card.layout.addLayout(row)
        grid.addWidget(saves_card, 0, 0)

        world_card = Card("Active world")
        self.overview_world = QLabel("None")
        self.overview_world.setWordWrap(True)
        self.overview_world.setObjectName("section")
        world_card.layout.addWidget(self.overview_world)
        self.overview_world_meta = QLabel("Open a save to inspect it.")
        self.overview_world_meta.setObjectName("muted")
        self.overview_world_meta.setWordWrap(True)
        world_card.layout.addWidget(self.overview_world_meta)
        grid.addWidget(world_card, 0, 1)

        ai_card = Card("AI providers")
        self.provider_summary = QLabel("Checking…")
        self.provider_summary.setWordWrap(True)
        ai_card.layout.addWidget(self.provider_summary)
        grid.addWidget(ai_card, 0, 2)
        root.addLayout(grid)

        saves = Card("Detected worlds")
        self.save_list = QListWidget()
        self.save_list.currentItemChanged.connect(self._preview_selection)
        self.save_list.itemDoubleClicked.connect(lambda _: self.open_selected())
        saves.layout.addWidget(self.save_list)
        row = QHBoxLayout()
        scan = QPushButton("Scan again")
        scan.clicked.connect(self.refresh_saves)
        row.addWidget(scan)
        open_btn2 = QPushButton("Open selected")
        open_btn2.setObjectName("primary")
        open_btn2.clicked.connect(self.open_selected)
        row.addWidget(open_btn2)
        row.addStretch()
        saves.layout.addLayout(row)
        root.addWidget(saves, 1)
        return page

    def _builder_page(self):
        page = QWidget()
        root = QVBoxLayout(page)
        root.setContentsMargins(4, 4, 4, 4)
        root.setSpacing(12)
        header = QHBoxLayout()
        title = QLabel("AI Builder")
        title.setObjectName("title")
        header.addWidget(title)
        header.addStretch()
        header.addWidget(QLabel("Build center"))
        root.addLayout(header)

        body = QHBoxLayout()
        left = QVBoxLayout()
        right = QVBoxLayout()

        prompt_card = Card("Describe your build")
        self.request = QPlainTextEdit()
        self.request.setMinimumHeight(190)
        self.request.setPlaceholderText(
            "Example: Create a cinematic mountain kingdom with a huge castle on a cliff, "
            "forests, rivers, roads, furnished interiors and a hidden redstone gate."
        )
        prompt_card.layout.addWidget(self.request)

        coords_card = Card("Build origin")
        coords = QGridLayout()
        self.x_spin = QSpinBox(); self.x_spin.setRange(-30000000, 30000000)
        self.y_spin = QSpinBox(); self.y_spin.setRange(-2048, 2048); self.y_spin.setValue(100)
        self.z_spin = QSpinBox(); self.z_spin.setRange(-30000000, 30000000)
        for col, (name, widget) in enumerate([("X", self.x_spin), ("Y", self.y_spin), ("Z", self.z_spin)]):
            coords.addWidget(QLabel(name), 0, col)
            coords.addWidget(widget, 1, col)
        coords_card.layout.addLayout(coords)
        left.append(prompt_card)
        left.append(coords_card)

        controls = QHBoxLayout()
        self.plan_btn = QPushButton("Plan with AI")
        self.plan_btn.setObjectName("primary")
        self.plan_btn.clicked.connect(self.make_plan)
        controls.addWidget(self.plan_btn)
        self.build_button = QPushButton("Backup + Build")
        self.build_button.setEnabled(False)
        self.build_button.clicked.connect(self.build_plan)
        controls.addWidget(self.build_button)
        controls.addStretch()
        left.append(controls)

        plan_card = Card("Plan preview")
        self.plan_output = QPlainTextEdit(); self.plan_output.setReadOnly(True)
        plan_card.layout.addWidget(self.plan_output)
        right.append(plan_card)

        console_card = Card("Generation console")
        self.console = QPlainTextEdit(); self.console.setReadOnly(True); self.console.setMaximumHeight(180)
        console_card.layout.addWidget(self.console)
        self.progress = QProgressBar(); self.progress.setRange(0, 0); self.progress.hide()
        console_card.layout.addWidget(self.progress)
        right.append(console_card)

        body.addLayout(left, 5)
        body.addLayout(right, 6)
        root.addLayout(body, 1)
        return page

    def _inspector_page(self):
        page = QWidget()
        root = QVBoxLayout(page); root.setContentsMargins(4, 4, 4, 4)
        title = QLabel("World Inspector"); title.setObjectName("title"); root.addWidget(title)
        card = Card("Save metadata and analysis")
        self.inspection = QPlainTextEdit(); self.inspection.setReadOnly(True); card.layout.addWidget(self.inspection)
        root.addWidget(card, 1)
        return page

    def _settings_page(self):
        page = QWidget()
        root = QVBoxLayout(page); root.setContentsMargins(4, 4, 4, 4)
        title = QLabel("Settings"); title.setObjectName("title"); root.addWidget(title)
        card = Card("AI providers")
        form = QFormLayout()
        self.openai_edit = QLineEdit(self.settings.openai_key)
        self.gemini_edit = QLineEdit(self.settings.gemini_key)
        self.openai_edit.setEchoMode(QLineEdit.Password); self.gemini_edit.setEchoMode(QLineEdit.Password)
        self.ollama_edit = QLineEdit(self.settings.ollama_url)
        self.ollama_model_edit = QLineEdit(self.settings.ollama_model)
        self.openai_model_edit = QLineEdit(self.settings.openai_model)
        self.gemini_model_edit = QLineEdit(self.settings.gemini_model)
        form.addRow("OpenAI API key", self.openai_edit)
        form.addRow("OpenAI model", self.openai_model_edit)
        form.addRow("Gemini API key", self.gemini_edit)
        form.addRow("Gemini model", self.gemini_model_edit)
        form.addRow("Ollama URL", self.ollama_edit)
        form.addRow("Ollama model", self.ollama_model_edit)
        card.layout.addLayout(form)
        self.backup_check = QCheckBox("Create a timestamped backup before building")
        self.backup_check.setChecked(self.settings.auto_backup)
        self.protect_check = QCheckBox("Protect player-built areas when planning")
        self.protect_check.setChecked(self.settings.protect_player_builds)
        card.layout.addWidget(self.backup_check); card.layout.addWidget(self.protect_check)
        row = QHBoxLayout()
        save = QPushButton("Save settings"); save.setObjectName("primary"); save.clicked.connect(self.save_settings)
        row.addWidget(save)
        test = QPushButton("Refresh provider status"); test.clicked.connect(self._refresh_provider_status); row.addWidget(test); row.addStretch()
        card.layout.addLayout(row)
        root.addWidget(card); root.addStretch()
        return page

    def _switch_page(self, index: int):
        self.pages.setCurrentIndex(index)
        names = ["Overview", "AI Builder", "World Inspector", "Settings"]
        self.page_title.setText(names[index])
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == index)

    def _preview_selection(self, item, _previous):
        if not item: return
        info = item.data(Qt.UserRole)
        self.active_world_chip.setText(info.name)
        self.overview_world.setText(info.name)
        self.overview_world_meta.setText(str(info.path))

    def refresh_saves(self):
        try:
            self.save_list.clear()
            self._saves = scan_saves()
            for save in self._saves:
                item = QListWidgetItem(save.name)
                item.setData(Qt.UserRole, save)
                self.save_list.addItem(item)
            self.overview_saves.setText(str(len(self._saves)))
            self.sidebar_status.setText(f"{len(self._saves)} saves detected")
            self.statusBar().showMessage(f"Detected {len(self._saves)} Minecraft saves")
        except Exception as exc:
            self.statusBar().showMessage(f"Save scan error: {exc}")

    def choose_folder(self):
        path = QFileDialog.getExistingDirectory(self, "Choose Minecraft saves folder")
        if not path: return
        self.save_list.clear()
        self._saves = scan_saves([Path(path)])
        for save in self._saves:
            item = QListWidgetItem(save.name); item.setData(Qt.UserRole, save); self.save_list.addItem(item)
        self.overview_saves.setText(str(len(self._saves)))
        self.sidebar_status.setText(f"{len(self._saves)} saves detected")

    def open_selected(self):
        item = self.save_list.currentItem()
        if not item:
            QMessageBox.information(self, "WorldSmith", "Select a world first.")
            return
        self.close_editor()
        self.current = item.data(Qt.UserRole)
        self.editor = WorldEditor(self.current.path)
        try:
            summary = self.editor.open()
            self.active_world_chip.setText(self.current.name)
            self.overview_world.setText(self.current.name)
            self.overview_world_meta.setText(f"{summary.platform} • {summary.version}")
            self.inspection.setPlainText(
                inspect_world(self.current.path)
                + f"\n\nAmulet chunks: {summary.chunks}\nBounds: {summary.bounds}\nDimensions: {', '.join(summary.dimensions)}"
            )
            self.console.appendPlainText(f"[WORLD] Opened {self.current.name}")
            self.statusBar().showMessage(f"Opened {self.current.name}")
            self._switch_page(1)
        except Exception as exc:
            self.close_editor(); QMessageBox.critical(self, "WorldSmith", str(exc))

    def save_settings(self):
        self.settings.openai_key = self.openai_edit.text().strip()
        self.settings.gemini_key = self.gemini_edit.text().strip()
        self.settings.ollama_url = self.ollama_edit.text().strip().rstrip("/")
        self.settings.ollama_model = self.ollama_model_edit.text().strip()
        self.settings.openai_model = self.openai_model_edit.text().strip()
        self.settings.gemini_model = self.gemini_model_edit.text().strip()
        self.settings.auto_backup = self.backup_check.isChecked()
        self.settings.protect_player_builds = self.protect_check.isChecked()
        self.settings.save(self.settings_path)
        self._refresh_provider_status()
        self.statusBar().showMessage("Settings saved")

    def _refresh_provider_status(self):
        configured = []
        if hasattr(self, "openai_edit") and self.openai_edit.text().strip(): configured.append("OpenAI")
        if hasattr(self, "gemini_edit") and self.gemini_edit.text().strip(): configured.append("Gemini")
        if self.settings.ollama_url: configured.append("Ollama")
        text = " • ".join(configured) if configured else "Offline planner only"
        if hasattr(self, "provider_summary"): self.provider_summary.setText(text)
        self.sidebar_status.setText(" • ".join(configured) if configured else "No cloud keys configured")

    def make_plan(self):
        if not self.current:
            QMessageBox.information(self, "WorldSmith", "Open a world first."); return
        request = self.request.toPlainText().strip()
        if not request: return
        self.save_settings()
        center = (self.x_spin.value(), self.y_spin.value(), self.z_spin.value())
        self.plan_btn.setEnabled(False); self.progress.show()
        self.console.appendPlainText("[AI] Running provider ensemble…")
        planner = Planner(Ensemble(self.settings))
        self._thread = QThread()
        self._worker = PlannerWorker(planner, request, inspect_world(self.current.path), center)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._plan_finished)
        self._worker.failed.connect(self._plan_failed)
        self._worker.finished.connect(self._thread.quit)
        self._worker.failed.connect(self._thread.quit)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.start()

    def _plan_finished(self, result):
        self.last_plan = result.plan
        self.plan_output.setPlainText(result.pretty())
        providers = ", ".join(r.provider for r in result.ensemble.responses) or "offline fallback"
        self.console.appendPlainText(f"[AI] Providers responded: {providers}")
        self.console.appendPlainText(f"[AI] Planned builds: {len(self.last_plan.get('builds', []))}")
        self.build_button.setEnabled(bool(self.last_plan.get("builds")))
        self.plan_btn.setEnabled(True); self.progress.hide()
        self.statusBar().showMessage(f"Plan ready • {providers}")

    def _plan_failed(self, message):
        self.plan_btn.setEnabled(True); self.progress.hide()
        self.console.appendPlainText(f"[ERROR] Planning failed: {message}")
        QMessageBox.critical(self, "Planning error", message)

    def build_plan(self):
        if not self.current or not self.last_plan: return
        try:
            self.close_editor()
            backup = backup_world(self.current.path) if self.settings.auto_backup else None
            self.editor = WorldEditor(self.current.path)
            self.editor.open()
            self.console.appendPlainText("[BUILD] Applying plan…")
            result = WorldBuilder(self.editor.require_level()).build(self.last_plan)
            self.editor.save(); self.close_editor()
            backup_text = f" • backup: {backup}" if backup else ""
            message = (
                f"Built {result.blocks_changed:,} blocks • {result.roads_changed:,} road blocks • "
                f"{result.systems_changed:,} redstone blocks{backup_text}"
            )
            self.console.appendPlainText(f"[BUILD] {message}")
            self.statusBar().showMessage(message)
            self.build_button.setEnabled(False)
        except Exception as exc:
            self.close_editor(); self.console.appendPlainText(f"[ERROR] Build failed: {exc}")
            QMessageBox.critical(self, "Build error", str(exc))

    def close_editor(self):
        if self.editor:
            try: self.editor.close()
            finally: self.editor = None

    def closeEvent(self, event):
        if self._thread and self._thread.isRunning():
            self._thread.quit(); self._thread.wait(1500)
        self.close_editor(); event.accept()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("WorldSmith AI")
    app.setFont(QFont("Segoe UI", 10))
    window = WorldSmithWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
