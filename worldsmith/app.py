from __future__ import annotations
import sys
from pathlib import Path
from worldsmith.backup import backup_world
from worldsmith.config import Settings
from worldsmith.context import inspect_world
from worldsmith.generation.builder import WorldBuilder
from worldsmith.planner import Planner
from worldsmith.scanner import SaveInfo,scan_saves
from worldsmith.ai.orchestrator import Ensemble
from worldsmith.world import WorldEditor

def main():
    from PySide6.QtWidgets import QApplication
    app=QApplication(sys.argv); w=WorldSmithWindow(); w.show(); return app.exec()

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox,QFileDialog,QFormLayout,QHBoxLayout,QLabel,QLineEdit,QListWidget,QListWidgetItem,QMainWindow,QMessageBox,QPlainTextEdit,QPushButton,QSpinBox,QTabWidget,QVBoxLayout,QWidget

class WorldSmithWindow(QMainWindow):
    def __init__(self):
        super().__init__(); self.setWindowTitle('WorldSmith AI — Minecraft World Architect'); self.resize(1200,800)
        self.settings_path=Path.home()/'.worldsmith'/'settings.json'; self.settings=Settings.load(self.settings_path); self.settings.apply_env(); self.current=None; self.editor=None; self.last_plan=None; self._saves=[]
        root=QWidget(); outer=QHBoxLayout(root); left=QVBoxLayout(); right=QVBoxLayout(); outer.addLayout(left,1); outer.addLayout(right,3)
        left.addWidget(QLabel('Minecraft Java Saves')); self.save_list=QListWidget(); left.addWidget(self.save_list)
        for text,fn in [('Refresh saves',self.refresh_saves),('Choose saves folder',self.choose_folder),('Open selected world',self.open_selected)]: b=QPushButton(text); b.clicked.connect(fn); left.addWidget(b)
        self.world_label=QLabel('No world open'); self.world_label.setWordWrap(True); left.addWidget(self.world_label)
        tabs=QTabWidget(); right.addWidget(tabs)
        chat=QWidget(); cl=QVBoxLayout(chat); self.request=QPlainTextEdit(); self.request.setPlaceholderText('Describe what WorldSmith should build…'); cl.addWidget(self.request)
        coords=QHBoxLayout(); self.x_spin=QSpinBox(); self.x_spin.setRange(-30000000,30000000); self.y_spin=QSpinBox(); self.y_spin.setRange(-2048,2048); self.y_spin.setValue(100); self.z_spin=QSpinBox(); self.z_spin.setRange(-30000000,30000000)
        for n,s in [('X',self.x_spin),('Y',self.y_spin),('Z',self.z_spin)]: coords.addWidget(QLabel(n)); coords.addWidget(s)
        cl.addLayout(coords); ask=QPushButton('Ask WorldSmith'); ask.clicked.connect(self.make_plan); cl.addWidget(ask); self.plan_output=QPlainTextEdit(); self.plan_output.setReadOnly(True); cl.addWidget(self.plan_output); self.build_button=QPushButton('Backup + Build plan into world'); self.build_button.clicked.connect(self.build_plan); self.build_button.setEnabled(False); cl.addWidget(self.build_button); tabs.addTab(chat,'AI Builder')
        info=QWidget(); il=QVBoxLayout(info); self.inspection=QPlainTextEdit(); self.inspection.setReadOnly(True); il.addWidget(self.inspection); tabs.addTab(info,'World info')
        settings=QWidget(); form=QFormLayout(settings); self.openai_edit=QLineEdit(self.settings.openai_key); self.gemini_edit=QLineEdit(self.settings.gemini_key)
        for e in (self.openai_edit,self.gemini_edit): e.setEchoMode(QLineEdit.Password)
        self.ollama_edit=QLineEdit(self.settings.ollama_url); self.ollama_model_edit=QLineEdit(self.settings.ollama_model); self.openai_model_edit=QLineEdit(self.settings.openai_model); self.gemini_model_edit=QLineEdit(self.settings.gemini_model)
        for n,e in [('OpenAI API key',self.openai_edit),('Gemini API key',self.gemini_edit),('Ollama URL',self.ollama_edit),('Ollama model',self.ollama_model_edit),('OpenAI model',self.openai_model_edit),('Gemini model',self.gemini_model_edit)]: form.addRow(n,e)
        self.backup_check=QCheckBox(); self.backup_check.setChecked(self.settings.auto_backup); form.addRow('Automatic backup',self.backup_check); save=QPushButton('Save settings'); save.clicked.connect(self.save_settings); form.addRow(save); tabs.addTab(settings,'Settings')
        self.status_label=QLabel('Ready'); right.addWidget(self.status_label); self.setCentralWidget(root); self.refresh_saves()
    def refresh_saves(self):
        self.save_list.clear(); self._saves=scan_saves()
        for s in self._saves: i=QListWidgetItem(s.name); i.setData(Qt.UserRole,s); self.save_list.addItem(i)
        self.status_label.setText(f'Found {len(self._saves)} saves')
    def choose_folder(self):
        p=QFileDialog.getExistingDirectory(self,'Choose Minecraft saves folder')
        if not p:return
        self.save_list.clear(); self._saves=scan_saves([Path(p)])
        for s in self._saves: i=QListWidgetItem(s.name); i.setData(Qt.UserRole,s); self.save_list.addItem(i)
    def open_selected(self):
        i=self.save_list.currentItem()
        if not i:return
        self.close_editor(); self.current=i.data(Qt.UserRole); self.editor=WorldEditor(self.current.path)
        try:
            summary=self.editor.open(); self.world_label.setText(f'Open: {summary.path.name}\nPlatform: {summary.platform}\nVersion: {summary.version}\nDimensions: {", ".join(summary.dimensions)}'); self.inspection.setPlainText(inspect_world(self.current.path)+f'\n\nAmulet chunks: {summary.chunks}\nBounds: {summary.bounds}'); self.status_label.setText('World opened')
        except Exception as exc: self.close_editor(); QMessageBox.critical(self,'WorldSmith',str(exc))
    def save_settings(self):
        self.settings.openai_key=self.openai_edit.text().strip(); self.settings.gemini_key=self.gemini_edit.text().strip(); self.settings.ollama_url=self.ollama_edit.text().strip().rstrip('/'); self.settings.ollama_model=self.ollama_model_edit.text().strip(); self.settings.openai_model=self.openai_model_edit.text().strip(); self.settings.gemini_model=self.gemini_model_edit.text().strip(); self.settings.auto_backup=self.backup_check.isChecked(); self.settings.save(self.settings_path)
    def make_plan(self):
        if not self.current: QMessageBox.information(self,'WorldSmith','Open a world first.'); return
        request=self.request.toPlainText().strip()
        if not request:return
        self.save_settings(); center=(self.x_spin.value(),self.y_spin.value(),self.z_spin.value())
        try:
            result=Planner(Ensemble(self.settings)).make_plan(request,inspect_world(self.current.path),center); self.last_plan=result.plan; self.plan_output.setPlainText(result.pretty()); providers=', '.join(r.provider for r in result.ensemble.responses) or 'offline fallback'; self.status_label.setText(f'Providers: {providers}'); self.build_button.setEnabled(bool(self.last_plan.get('builds')))
        except Exception as exc: QMessageBox.critical(self,'Planning error',str(exc))
    def build_plan(self):
        if not self.current or not self.last_plan:return
        try:
            self.close_editor(); backup=backup_world(self.current.path) if self.settings.auto_backup else None; self.editor=WorldEditor(self.current.path); self.editor.open(); r=WorldBuilder(self.editor.require_level()).build(self.last_plan); self.editor.save(); self.close_editor(); self.status_label.setText(f'Built {r.blocks_changed} blocks, {r.roads_changed} road blocks, {r.systems_changed} redstone blocks.' + (f' Backup: {backup}' if backup else '')); self.build_button.setEnabled(False)
        except Exception as exc: self.close_editor(); QMessageBox.critical(self,'Build error',str(exc))
    def close_editor(self):
        if self.editor:
            try:self.editor.close()
            finally:self.editor=None
    def closeEvent(self,event): self.close_editor(); event.accept()
