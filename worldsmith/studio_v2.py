from __future__ import annotations

import json
import time
from pathlib import Path

from PySide6.QtCore import QObject, QThread, Qt, Signal
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QFileDialog, QFormLayout, QGridLayout, QHBoxLayout,
    QLabel, QLineEdit, QListWidget, QListWidgetItem, QMainWindow, QMessageBox,
    QPlainTextEdit, QProgressBar, QPushButton, QSpinBox, QTabWidget, QVBoxLayout,
    QWidget
)

from worldsmith.audit import BuildAudit
from worldsmith.backup import backup_world
from worldsmith.config import Settings
from worldsmith.context import inspect_world
from worldsmith.generation.builder import WorldBuilder
from worldsmith.planner import Planner
from worldsmith.ai.orchestrator import Ensemble
from worldsmith.memory import MemoryStore
from worldsmith.preview import Preview3D
from worldsmith.scanner import scan_saves
from worldsmith.world import WorldEditor


STYLE = """
QMainWindow,QWidget { background:#070b14; color:#edf2ff; font-family:'Segoe UI'; font-size:13px; }
QTabWidget::pane { border:1px solid #202b45; background:#0b1220; border-radius:10px; }
QTabBar::tab { background:#10182a; padding:10px 18px; margin-right:3px; border:1px solid #202b45; }
QTabBar::tab:selected { background:#1b2d55; }
QFrame,QListWidget,QPlainTextEdit,QLineEdit,QSpinBox { background:#0a1220; border:1px solid #253453; border-radius:9px; }
QPushButton { background:#14213a; border:1px solid #30466f; border-radius:8px; padding:9px 14px; }
QPushButton:hover { background:#1b3157; }
QPushButton#primary { background:#536dff; border-color:#7388ff; font-weight:700; }
QPushButton#danger { background:#351d29; border-color:#704052; }
QLabel#title { font-size:25px; font-weight:800; }
QLabel#muted { color:#8996b2; }
QLabel#metric { font-size:24px; font-weight:800; }
QProgressBar { height:14px; border-radius:7px; text-align:center; }
QProgressBar::chunk { background:#6278ff; border-radius:7px; }
"""


class BuildWorker(QObject):
    progress = Signal(int, str)
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, path: Path, plan: dict, do_backup: bool):
        super().__init__()
        self.path, self.plan, self.do_backup = path, plan, do_backup

    def run(self):
        started = time.monotonic()
        audit = BuildAudit.start(self.path, self.plan)
        backup = None
        editor = None
        try:
            self.progress.emit(5, 'Checking world and plan safety')
            if self.do_backup:
                self.progress.emit(10, 'Creating timestamped world backup')
                backup = backup_world(self.path)
            self.progress.emit(18, 'Opening Minecraft Java save')
            editor = WorldEditor(self.path)
            editor.open()
            self.progress.emit(25, 'Generating terrain, structures and systems')
            result = WorldBuilder(editor.require_level(), seed=int(self.plan.get('seed', 1337))).build(self.plan)
            self.progress.emit(82, 'Saving modified chunks')
            editor.save()
            self.progress.emit(94, 'Finalizing build audit')
            audit.finish(result, backup, started_monotonic=started)
            report = audit.save()
            self.progress.emit(100, 'Build complete')
            self.finished.emit({'result': result, 'backup': backup, 'report': report})
        except Exception as exc:
            audit.finish(backup_path=backup, errors=[str(exc)], started_monotonic=started)
            try: audit.save()
            except Exception: pass
            self.failed.emit(str(exc))
        finally:
            if editor is not None:
                try: editor.close()
                except Exception: pass


class PlannerWorker(QObject):
    finished = Signal(object)
    failed = Signal(str)
    activity = Signal(str)

    def __init__(self, planner, request, context, center):
        super().__init__()
        self.planner, self.request, self.context, self.center = planner, request, context, center

    def run(self):
        try:
            self.finished.emit(self.planner.make_plan(self.request, self.context, self.center, activity=self.activity.emit))
        except Exception as exc:
            self.failed.emit(str(exc))


class WorldSmithStudio(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('WorldSmith AI — Studio V2')
        self.resize(1500, 930)
        self.setStyleSheet(STYLE)
        self.settings_path = Path.home() / '.worldsmith' / 'settings.json'
        self.settings = Settings.load(self.settings_path)
        self.settings.apply_env()
        self.memory = MemoryStore(Path.home() / '.worldsmith' / 'memory.db')
        self.saves = []
        self.current = None
        self.plan = None
        self.threads = []
        self._ui()
        self.scan()

    def _ui(self):
        root = QWidget(); outer = QVBoxLayout(root); outer.setContentsMargins(18,18,18,18)
        head = QHBoxLayout()
        title = QLabel('WorldSmith AI'); title.setObjectName('title'); head.addWidget(title)
        subtitle = QLabel('Standalone Minecraft Java world studio • real .minecraft saves'); subtitle.setObjectName('muted'); head.addWidget(subtitle); head.addStretch()
        self.world_label = QLabel('No world selected'); head.addWidget(self.world_label)
        outer.addLayout(head)

        tabs = QTabWidget(); outer.addWidget(tabs, 1)
        tabs.addTab(self._world_tab(), 'Worlds')
        tabs.addTab(self._build_tab(), 'AI Builder')
        tabs.addTab(self._preview_tab(), '3D Preview')
        tabs.addTab(self._inspect_tab(), 'Inspector')
        tabs.addTab(self._settings_tab(), 'Settings')
        self.setCentralWidget(root)
        self.statusBar().showMessage('Ready')

    def _world_tab(self):
        page=QWidget(); lay=QVBoxLayout(page)
        top=QHBoxLayout(); b=QPushButton('Scan Minecraft + TLauncher saves'); b.setObjectName('primary'); b.clicked.connect(self.scan); top.addWidget(b)
        choose=QPushButton('Add saves folder'); choose.clicked.connect(self.choose_folder); top.addWidget(choose); top.addStretch(); lay.addLayout(top)
        grid=QGridLayout(); self.count=QLabel('0'); self.count.setObjectName('metric'); grid.addWidget(self.count,0,0)
        grid.addWidget(QLabel('detected worlds'),1,0); self.path_label=QLabel('Select a world to inspect'); self.path_label.setObjectName('muted'); grid.addWidget(self.path_label,0,1,2,2); lay.addLayout(grid)
        self.worlds=QListWidget(); self.worlds.currentItemChanged.connect(self.select_world); lay.addWidget(self.worlds,1)
        return page

    def _build_tab(self):
        page=QWidget(); lay=QVBoxLayout(page)
        self.request=QPlainTextEdit(); self.request.setMinimumHeight(150); self.request.setPlaceholderText('Example: Build a massive mountain kingdom with a cliff castle, connected districts, rivers, bridges, roads, furnished interiors and a functional gate.')
        lay.addWidget(self.request)
        form=QFormLayout(); row=QHBoxLayout(); self.x=QSpinBox(); self.x.setRange(-30000000,30000000); self.y=QSpinBox(); self.y.setRange(-2048,2048); self.y.setValue(100); self.z=QSpinBox(); self.z.setRange(-30000000,30000000)
        for label,w in [('X',self.x),('Y',self.y),('Z',self.z)]: row.addWidget(QLabel(label)); row.addWidget(w)
        form.addRow('Build center',row); lay.addLayout(form)
        controls=QHBoxLayout(); self.plan_btn=QPushButton('PLAN + QUALITY CHECK'); self.plan_btn.setObjectName('primary'); self.plan_btn.clicked.connect(self.make_plan); controls.addWidget(self.plan_btn)
        self.build_btn=QPushButton('BACKUP + BUILD REAL SAVE'); self.build_btn.setObjectName('primary'); self.build_btn.setEnabled(False); self.build_btn.clicked.connect(self.build); controls.addWidget(self.build_btn)
        self.backup=QCheckBox('backup before build'); self.backup.setChecked(True); controls.addWidget(self.backup); controls.addStretch(); lay.addLayout(controls)
        self.progress=QProgressBar(); self.progress.setRange(0,100); self.progress.setValue(0); lay.addWidget(self.progress)
        split=QHBoxLayout(); self.plan_output=QPlainTextEdit(); self.plan_output.setReadOnly(True); self.activity=QPlainTextEdit(); self.activity.setReadOnly(True); split.addWidget(self.plan_output,3); split.addWidget(self.activity,2); lay.addLayout(split,1)
        return page

    def _preview_tab(self):
        page=QWidget(); lay=QVBoxLayout(page); self.preview=Preview3D(); lay.addWidget(self.preview,1); return page

    def _inspect_tab(self):
        page=QWidget(); lay=QVBoxLayout(page); self.inspection=QPlainTextEdit(); self.inspection.setReadOnly(True); lay.addWidget(self.inspection,1); return page

    def _settings_tab(self):
        page=QWidget(); lay=QVBoxLayout(page); form=QFormLayout()
        self.oa=QLineEdit(self.settings.openai_model); self.gm=QLineEdit(self.settings.gemini_model); self.om=QLineEdit(self.settings.ollama_model); self.ou=QLineEdit(self.settings.ollama_url)
        for n,w in [('OpenAI model',self.oa),('Gemini model',self.gm),('Ollama model',self.om),('Ollama URL',self.ou)]: form.addRow(n,w)
        lay.addLayout(form); save=QPushButton('Save provider settings'); save.setObjectName('primary'); save.clicked.connect(self.save_settings); lay.addWidget(save); lay.addStretch(); return page

    def scan(self):
        self.saves=scan_saves(); self.worlds.clear()
        for save in self.saves:
            item=QListWidgetItem(f'{save.name}   •   {save.path}'); item.setData(Qt.UserRole,save); self.worlds.addItem(item)
        self.count.setText(str(len(self.saves))); self.statusBar().showMessage(f'{len(self.saves)} Minecraft worlds detected')

    def choose_folder(self):
        folder=QFileDialog.getExistingDirectory(self,'Choose saves folder')
        if not folder:return
        self.saves=scan_saves([Path(folder)]); self.worlds.clear()
        for save in self.saves:
            item=QListWidgetItem(f'{save.name}   •   {save.path}'); item.setData(Qt.UserRole,save); self.worlds.addItem(item)
        self.count.setText(str(len(self.saves)))

    def select_world(self,item,_):
        if not item:return
        self.current=item.data(Qt.UserRole); self.world_label.setText(self.current.name); self.path_label.setText(str(self.current.path))
        try:self.inspection.setPlainText(inspect_world(self.current.path))
        except Exception as exc:self.inspection.setPlainText(f'Inspector error: {exc}')

    def save_settings(self):
        self.settings.openai_model=self.oa.text().strip() or self.settings.openai_model
        self.settings.gemini_model=self.gm.text().strip() or self.settings.gemini_model
        self.settings.ollama_model=self.om.text().strip() or self.settings.ollama_model
        self.settings.ollama_url=self.ou.text().strip().rstrip('/') or self.settings.ollama_url
        self.settings.save(self.settings_path); self.statusBar().showMessage('Settings saved')

    def make_plan(self):
        if not self.current: QMessageBox.information(self,'WorldSmith','Select a world first.'); return
        text=self.request.toPlainText().strip()
        if not text:return
        self.save_settings(); self.plan=None; self.build_btn.setEnabled(False); self.plan_btn.setEnabled(False); self.activity.clear(); self.progress.setValue(0)
        center=(self.x.value(),self.y.value(),self.z.value())
        context=(inspect_world(self.current.path)+'\n\n'+self.memory.build_context(text,str(self.current.path))+'\n\nPLAYER_BUILD_PROTECTION=True')[:16000]
        self.thread=QThread(); self.worker=PlannerWorker(Planner(Ensemble(self.settings)),text,context,center); self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run); self.worker.activity.connect(self.activity.appendPlainText); self.worker.finished.connect(self.plan_done); self.worker.failed.connect(self.plan_failed); self.worker.finished.connect(self.thread.quit); self.worker.failed.connect(self.thread.quit); self.thread.finished.connect(lambda:self.plan_btn.setEnabled(True)); self.thread.start(); self.threads.append(self.thread)

    def plan_done(self,result):
        self.plan=result.plan; self.plan_output.setPlainText(result.pretty()); self.preview.set_plan(self.plan); self.build_btn.setEnabled(bool(self.plan.get('builds') or self.plan.get('terrain',{}).get('enabled'))); self.activity.appendPlainText('Quality gate passed: plan sanitized and repair-checked. Ready to write real chunks.')

    def plan_failed(self,msg): self.activity.appendPlainText('ERROR: '+msg); QMessageBox.critical(self,'Planning error',msg)

    def build(self):
        if not self.current or not self.plan:return
        self.build_btn.setEnabled(False); self.progress.setValue(1)
        self.thread=QThread(); self.worker=BuildWorker(self.current.path,self.plan,self.backup.isChecked()); self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run); self.worker.progress.connect(self.progress.setValue); self.worker.progress.connect(lambda n,m:self.activity.appendPlainText(m)); self.worker.finished.connect(self.build_done); self.worker.failed.connect(self.build_failed); self.worker.finished.connect(self.thread.quit); self.worker.failed.connect(self.thread.quit); self.thread.finished.connect(lambda:self.build_btn.setEnabled(True)); self.thread.start(); self.threads.append(self.thread)

    def build_done(self,payload):
        result=payload['result']; backup=payload['backup']; report=payload['report']; self.activity.appendPlainText(f"DONE • {result.blocks_changed} blocks • {result.structures_changed} structures • {result.roads_changed} road blocks • {result.systems_changed} redstone blocks")
        self.statusBar().showMessage(f'Build complete. Audit: {report}')
        QMessageBox.information(self,'WorldSmith build complete',f"Blocks changed: {result.blocks_changed}\nStructures: {result.structures_changed}\nRoad blocks: {result.roads_changed}\nRedstone blocks: {result.systems_changed}\n\nBackup: {backup or 'disabled'}\nAudit: {report}")

    def build_failed(self,msg): self.activity.appendPlainText('BUILD ERROR: '+msg); QMessageBox.critical(self,'Build failed',msg)


def main():
    app=QApplication([]); app.setApplicationName('WorldSmith AI'); window=WorldSmithStudio(); window.show(); return app.exec()
