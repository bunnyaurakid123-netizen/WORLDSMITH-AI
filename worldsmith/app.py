from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QObject, QThread, Qt, Signal
from PySide6.QtGui import QSurfaceFormat
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
from worldsmith.auth import GoogleAuth, GoogleAuthError
from worldsmith.backup import backup_world
from worldsmith.config import Settings
from worldsmith.context import inspect_world
from worldsmith.generation.builder import WorldBuilder
from worldsmith.memory import MemoryStore
from worldsmith.planner import Planner
from worldsmith.preview import Preview3D
from worldsmith.scanner import scan_saves
from worldsmith.world import WorldEditor


APP_STYLE = """
QMainWindow, QWidget { background:#080d18; color:#e9eefc; font-family:'Segoe UI'; font-size:13px; }
QFrame#sidebar { background:#060a12; border-right:1px solid #1c2740; }
QFrame#topbar, QFrame#card { background:#0f1627; border:1px solid #1e2a44; border-radius:14px; }
QFrame#hero { background:#101a31; border:1px solid #2a3d70; border-radius:18px; }
QLabel#brand { font-size:21px; font-weight:800; }
QLabel#title { font-size:25px; font-weight:800; }
QLabel#section { font-size:15px; font-weight:700; }
QLabel#muted { color:#8995b0; }
QLabel#metric { font-size:27px; font-weight:800; }
QLabel#chip { background:#17233d; border:1px solid #29406c; border-radius:11px; padding:6px 10px; }
QPushButton { background:#141f35; color:#ecf1ff; border:1px solid #293858; border-radius:9px; padding:9px 13px; }
QPushButton:hover { background:#1b2a49; border-color:#526ca8; }
QPushButton#primary { background:#4d6bff; border-color:#6b82ff; font-weight:700; }
QPushButton#primary:hover { background:#5c78ff; }
QPushButton#danger { background:#321a24; border-color:#653344; }
QPushButton#nav { text-align:left; padding:11px 13px; background:transparent; border:0; color:#9aa7c1; }
QPushButton#nav:hover { background:#10192c; color:white; }
QPushButton#nav:checked { background:#182545; color:white; border-left:3px solid #6a7dff; }
QLineEdit, QPlainTextEdit, QListWidget, QSpinBox { background:#0a1120; color:#e9eefc; border:1px solid #26334d; border-radius:9px; padding:8px; }
QListWidget::item { padding:10px; margin:3px 0; border-radius:8px; }
QListWidget::item:selected { background:#17274c; border:1px solid #3c548c; }
QProgressBar { background:#09101e; border:1px solid #24314b; border-radius:7px; text-align:center; height:13px; }
QProgressBar::chunk { background:#6479ff; border-radius:7px; }
QCheckBox { spacing:8px; }
"""


class Card(QFrame):
    def __init__(self, title: str | None = None):
        super().__init__()
        self.setObjectName("card")
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(16, 16, 16, 16)
        self.layout.setSpacing(10)
        if title:
            heading = QLabel(title)
            heading.setObjectName("section")
            self.layout.addWidget(heading)


class PlannerWorker(QObject):
    finished = Signal(object)
    failed = Signal(str)
    activity = Signal(str)

    def __init__(self, planner: Planner, request: str, context: str, center: tuple[int, int, int]):
        super().__init__()
        self.planner = planner
        self.request = request
        self.context = context
        self.center = center

    def run(self):
        try:
            result = self.planner.make_plan(self.request, self.context, self.center, activity=self.activity.emit)
            self.finished.emit(result)
        except Exception as exc:
            self.failed.emit(str(exc))


class WorldSmithWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("WorldSmith AI")
        self.resize(1480, 920)
        self.setMinimumSize(1180, 760)

        self.settings_path = Path.home() / ".worldsmith" / "settings.json"
        self.settings = Settings.load(self.settings_path)
        self.settings.apply_env()
        if not self.settings.google_client_secret:
            self.settings.google_client_secret = str(Path.home() / ".worldsmith" / "google_client_secret.json")
        self.memory = MemoryStore(Path.home() / ".worldsmith" / "memory.db")
        self.current = None
        self.editor = None
        self.last_plan: dict | None = None
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

        sidebar = QFrame(); sidebar.setObjectName("sidebar"); sidebar.setFixedWidth(225)
        sl = QVBoxLayout(sidebar); sl.setContentsMargins(16, 20, 16, 16); sl.setSpacing(5)
        brand = QLabel("WORLDsmith"); brand.setObjectName("brand"); sl.addWidget(brand)
        sub = QLabel("AI Minecraft world studio"); sub.setObjectName("muted"); sl.addWidget(sub); sl.addSpacing(22)
        self.nav_buttons = []
        for label, index in [("Overview",0),("AI Builder",1),("3D Preview",2),("Memory",3),("World Inspector",4),("Settings",5)]:
            b = QPushButton(label); b.setObjectName("nav"); b.setCheckable(True)
            b.clicked.connect(lambda checked, i=index: self._switch_page(i)); sl.addWidget(b); self.nav_buttons.append(b)
        self.nav_buttons[0].setChecked(True)
        sl.addStretch()
        self.sidebar_account = QLabel("Not signed in"); self.sidebar_account.setObjectName("muted"); self.sidebar_account.setWordWrap(True); sl.addWidget(self.sidebar_account)
        self.sidebar_status = QLabel("Ready"); self.sidebar_status.setObjectName("muted"); sl.addWidget(self.sidebar_status)
        outer.addWidget(sidebar)

        content = QWidget(); main = QVBoxLayout(content); main.setContentsMargins(18,18,18,18); main.setSpacing(14)
        top = QFrame(); top.setObjectName("topbar"); tl = QHBoxLayout(top); tl.setContentsMargins(16,10,16,10)
        self.page_title = QLabel("Overview"); self.page_title.setObjectName("section"); tl.addWidget(self.page_title); tl.addStretch()
        self.world_chip = QLabel("No world selected"); self.world_chip.setObjectName("chip"); tl.addWidget(self.world_chip)
        self.account_chip = QLabel(self.settings.google_email or "Guest"); self.account_chip.setObjectName("chip"); tl.addWidget(self.account_chip)
        main.addWidget(top)

        self.pages = QStackedWidget()
        self.pages.addWidget(self._overview_page()); self.pages.addWidget(self._builder_page()); self.pages.addWidget(self._preview_page())
        self.pages.addWidget(self._memory_page()); self.pages.addWidget(self._inspector_page()); self.pages.addWidget(self._settings_page())
        main.addWidget(self.pages,1); outer.addWidget(content,1); self.setCentralWidget(root); self.statusBar().showMessage("WorldSmith ready")

    def _overview_page(self):
        page = QWidget(); root = QVBoxLayout(page); root.setContentsMargins(4,4,4,4); root.setSpacing(14)
        hero = QFrame(); hero.setObjectName("hero"); hl = QVBoxLayout(hero); hl.setContentsMargins(24,22,24,22)
        t=QLabel("Build worlds with intent."); t.setObjectName("title"); hl.addWidget(t)
        d=QLabel("Generate terrain, settlements, interiors and redstone plans, preview them in 3D, then write the result into a real Minecraft Java save."); d.setObjectName("muted"); d.setWordWrap(True); hl.addWidget(d)
        actions=QHBoxLayout(); openb=QPushButton("Open selected world"); openb.setObjectName("primary"); openb.clicked.connect(self.open_selected); actions.addWidget(openb)
        scan=QPushButton("Scan saves"); scan.clicked.connect(self.refresh_saves); actions.addWidget(scan); actions.addStretch(); hl.addLayout(actions); root.addWidget(hero)
        grid=QGridLayout(); grid.setHorizontalSpacing(14); grid.setVerticalSpacing(14)
        for c in range(3): grid.setColumnStretch(c,1)
        c1=Card("Minecraft worlds"); self.overview_saves=QLabel("0"); self.overview_saves.setObjectName("metric"); c1.layout.addWidget(self.overview_saves); grid.addWidget(c1,0,0)
        c2=Card("Active world"); self.overview_world=QLabel("None"); self.overview_world.setObjectName("section"); self.overview_world.setWordWrap(True); c2.layout.addWidget(self.overview_world); self.overview_meta=QLabel("Choose a save to get started."); self.overview_meta.setObjectName("muted"); self.overview_meta.setWordWrap(True); c2.layout.addWidget(self.overview_meta); grid.addWidget(c2,0,1)
        c3=Card("AI ensemble"); self.provider_summary=QLabel("Checking configuration…"); self.provider_summary.setWordWrap(True); c3.layout.addWidget(self.provider_summary); grid.addWidget(c3,0,2)
        root.addLayout(grid)
        worlds=Card("Detected saves"); self.save_list=QListWidget(); self.save_list.currentItemChanged.connect(self._preview_selection); self.save_list.itemDoubleClicked.connect(lambda _:self.open_selected()); worlds.layout.addWidget(self.save_list)
        row=QHBoxLayout(); b=QPushButton("Open selected"); b.setObjectName("primary"); b.clicked.connect(self.open_selected); row.addWidget(b); row.addStretch(); worlds.layout.addLayout(row); root.addWidget(worlds,1); return page

    def _builder_page(self):
        page=QWidget(); root=QVBoxLayout(page); root.setContentsMargins(4,4,4,4); root.setSpacing(12)
        head=QHBoxLayout(); t=QLabel("AI Builder"); t.setObjectName("title"); head.addWidget(t); head.addStretch(); head.addWidget(QLabel("AI activity shows progress summaries, not private chain-of-thought")); root.addLayout(head)
        body=QHBoxLayout(); left=QVBoxLayout(); right=QVBoxLayout()
        prompt=Card("Describe what to build"); self.request=QPlainTextEdit(); self.request.setMinimumHeight(190); self.request.setPlaceholderText("Create a huge snowy mountain kingdom with a castle on a cliff, forests, rivers, roads, detailed interiors and functional redstone gates…"); prompt.layout.addWidget(self.request); left.addWidget(prompt)
        origin=Card("Build origin"); coords=QGridLayout(); self.x_spin=QSpinBox(); self.x_spin.setRange(-30000000,30000000); self.y_spin=QSpinBox(); self.y_spin.setRange(-2048,2048); self.y_spin.setValue(100); self.z_spin=QSpinBox(); self.z_spin.setRange(-30000000,30000000)
        for col,(name,w) in enumerate([("X",self.x_spin),("Y",self.y_spin),("Z",self.z_spin)]): coords.addWidget(QLabel(name),0,col); coords.addWidget(w,1,col)
        origin.layout.addLayout(coords); left.addWidget(origin)
        controls=QHBoxLayout(); self.plan_btn=QPushButton("Plan + Preview"); self.plan_btn.setObjectName("primary"); self.plan_btn.clicked.connect(self.make_plan); controls.addWidget(self.plan_btn); self.build_button=QPushButton("Backup + Build"); self.build_button.setEnabled(False); self.build_button.clicked.connect(self.build_plan); controls.addWidget(self.build_button); controls.addStretch(); left.addLayout(controls)
        pcard=Card("Plan preview"); self.plan_output=QPlainTextEdit(); self.plan_output.setReadOnly(True); pcard.layout.addWidget(self.plan_output); right.addWidget(pcard,1)
        acard=Card("AI activity"); self.activity=QPlainTextEdit(); self.activity.setReadOnly(True); self.activity.setMaximumHeight(230); acard.layout.addWidget(self.activity); self.progress=QProgressBar(); self.progress.setRange(0,0); self.progress.hide(); acard.layout.addWidget(self.progress); right.addWidget(acard)
        body.addLayout(left,5); body.addLayout(right,6); root.addLayout(body,1); return page

    def _preview_page(self):
        page=QWidget(); root=QVBoxLayout(page); root.setContentsMargins(4,4,4,4); head=QHBoxLayout(); t=QLabel("3D Preview"); t.setObjectName("title"); head.addWidget(t); head.addStretch(); head.addWidget(QLabel("Drag to orbit • wheel to zoom")); root.addLayout(head); card=Card(); self.preview=Preview3D(); card.layout.addWidget(self.preview,1); root.addWidget(card,1); return page

    def _memory_page(self):
        page=QWidget(); root=QVBoxLayout(page); root.setContentsMargins(4,4,4,4); head=QHBoxLayout(); t=QLabel("AI Memory"); t.setObjectName("title"); head.addWidget(t); head.addStretch(); head.addWidget(QLabel("Stored locally on this PC")); root.addLayout(head)
        card=Card("Long-term memories"); self.memory_list=QListWidget(); card.layout.addWidget(self.memory_list,1)
        self.memory_input=QPlainTextEdit(); self.memory_input.setPlaceholderText("Example: Prefer dramatic mountains, warm medieval interiors, and spruce/stone architecture."); self.memory_input.setMaximumHeight(90); card.layout.addWidget(self.memory_input)
        row=QHBoxLayout(); add=QPushButton("Remember"); add.setObjectName("primary"); add.clicked.connect(self.add_memory); row.addWidget(add); forget=QPushButton("Forget selected"); forget.setObjectName("danger"); forget.clicked.connect(self.forget_memory); row.addWidget(forget); row.addStretch(); card.layout.addLayout(row); root.addWidget(card,1); return page

    def _inspector_page(self):
        page=QWidget(); root=QVBoxLayout(page); root.setContentsMargins(4,4,4,4); t=QLabel("World Inspector"); t.setObjectName("title"); root.addWidget(t); card=Card("Save metadata and analysis"); self.inspection=QPlainTextEdit(); self.inspection.setReadOnly(True); card.layout.addWidget(self.inspection); root.addWidget(card,1); return page

    def _settings_page(self):
        page=QWidget(); root=QVBoxLayout(page); root.setContentsMargins(4,4,4,4); t=QLabel("Settings"); t.setObjectName("title"); root.addWidget(t)
        card=Card("AI providers"); form=QFormLayout(); self.openai_edit=QLineEdit(self.settings.openai_key); self.gemini_edit=QLineEdit(self.settings.gemini_key); self.openai_edit.setEchoMode(QLineEdit.Password); self.gemini_edit.setEchoMode(QLineEdit.Password)
        self.openai_model_edit=QLineEdit(self.settings.openai_model); self.gemini_model_edit=QLineEdit(self.settings.gemini_model); self.ollama_edit=QLineEdit(self.settings.ollama_url); self.ollama_model_edit=QLineEdit(self.settings.ollama_model)
        for label,w in [("OpenAI API key",self.openai_edit),("OpenAI model",self.openai_model_edit),("Gemini API key",self.gemini_edit),("Gemini model",self.gemini_model_edit),("Ollama URL",self.ollama_edit),("Ollama model",self.ollama_model_edit)]: form.addRow(label,w)
        card.layout.addLayout(form); self.backup_check=QCheckBox("Create a timestamped backup before building"); self.backup_check.setChecked(self.settings.auto_backup); card.layout.addWidget(self.backup_check); self.protect_check=QCheckBox("Protect player-built areas in the planning rules"); self.protect_check.setChecked(self.settings.protect_player_builds); card.layout.addWidget(self.protect_check); root.addWidget(card)
        google=Card("Google account"); gf=QFormLayout(); self.google_secret_edit=QLineEdit(self.settings.google_client_secret); gf.addRow("OAuth desktop client JSON",self.google_secret_edit); google.layout.addLayout(gf)
        gline=QHBoxLayout(); browse=QPushButton("Choose client JSON"); browse.clicked.connect(self.choose_google_secret); gline.addWidget(browse); self.signin=QPushButton("Sign in with Google"); self.signin.setObjectName("primary"); self.signin.clicked.connect(self.google_signin); gline.addWidget(self.signin); signout=QPushButton("Sign out"); signout.clicked.connect(self.google_signout); gline.addWidget(signout); google.layout.addLayout(gline)
        self.google_note=QLabel("Uses Google identity (OpenID Connect) for login. WorldSmith does not request Gmail message access."); self.google_note.setObjectName("muted"); self.google_note.setWordWrap(True); google.layout.addWidget(self.google_note); root.addWidget(google)
        save=QPushButton("Save settings"); save.setObjectName("primary"); save.clicked.connect(self.save_settings); root.addWidget(save); root.addStretch(); return page

    def _switch_page(self,index:int):
        self.pages.setCurrentIndex(index); names=["Overview","AI Builder","3D Preview","Memory","World Inspector","Settings"]; self.page_title.setText(names[index])
        for i,b in enumerate(self.nav_buttons): b.setChecked(i==index)

    def refresh_saves(self):
        self.save_list.clear(); self._saves=scan_saves(); self.overview_saves.setText(str(len(self._saves)))
        for save in self._saves: item=QListWidgetItem(save.name); item.setData(Qt.UserRole,save); self.save_list.addItem(item)
        self.sidebar_status.setText(f"{len(self._saves)} saves found"); self.statusBar().showMessage(f"Detected {len(self._saves)} Minecraft saves")

    def choose_folder(self):
        folder=QFileDialog.getExistingDirectory(self,"Choose Minecraft saves folder")
        if not folder:return
        self.save_list.clear(); self._saves=scan_saves([Path(folder)]); self.overview_saves.setText(str(len(self._saves)))
        for save in self._saves: item=QListWidgetItem(save.name); item.setData(Qt.UserRole,save); self.save_list.addItem(item)

    def _preview_selection(self,current,_previous):
        if not current:return
        save=current.data(Qt.UserRole); self.world_chip.setText(save.name); self.overview_world.setText(save.name); self.overview_meta.setText(str(save.path))

    def open_selected(self):
        item=self.save_list.currentItem()
        if not item: QMessageBox.information(self,"WorldSmith","Select a Minecraft world first."); return
        self.close_editor(); self.current=item.data(Qt.UserRole); self.editor=WorldEditor(self.current.path)
        try:
            summary=self.editor.open(); self.world_chip.setText(summary.path.name); self.overview_world.setText(summary.path.name); self.overview_meta.setText(f"{summary.platform} • {summary.version}"); self.inspection.setPlainText(inspect_world(self.current.path)+f"\n\nAmulet chunks: {summary.chunks}\nBounds: {summary.bounds}"); self.sidebar_status.setText(f"Open: {summary.path.name}"); self.statusBar().showMessage("World opened"); self._switch_page(1)
        except Exception as exc: self.close_editor(); QMessageBox.critical(self,"WorldSmith",str(exc))

    def save_settings(self):
        self.settings.openai_key=self.openai_edit.text().strip(); self.settings.gemini_key=self.gemini_edit.text().strip(); self.settings.openai_model=self.openai_model_edit.text().strip(); self.settings.gemini_model=self.gemini_model_edit.text().strip(); self.settings.ollama_url=self.ollama_edit.text().strip().rstrip('/'); self.settings.ollama_model=self.ollama_model_edit.text().strip(); self.settings.auto_backup=self.backup_check.isChecked(); self.settings.protect_player_builds=self.protect_check.isChecked(); self.settings.google_client_secret=self.google_secret_edit.text().strip(); self.settings.save(self.settings_path); self._refresh_provider_status(); self.statusBar().showMessage("Settings saved")

    def _refresh_provider_status(self):
        states=[f"OpenAI: {'ready' if self.settings.openai_key else 'key needed'}",f"Gemini: {'ready' if self.settings.gemini_key else 'key needed'}",f"Ollama: {self.settings.ollama_model}"]
        self.provider_summary.setText("\n".join(states))
        if self.settings.google_email:
            self.account_chip.setText(self.settings.google_email); self.sidebar_account.setText(f"Signed in\n{self.settings.google_email}")

    def make_plan(self):
        if not self.current: QMessageBox.information(self,"WorldSmith","Open a world first."); return
        request=self.request.toPlainText().strip()
        if not request:return
        self.save_settings(); self.last_plan=None; self.build_button.setEnabled(False); self.activity.clear(); self.activity.appendPlainText("WorldSmith • starting ensemble analysis"); self.progress.show(); self.plan_btn.setEnabled(False)
        center=(self.x_spin.value(),self.y_spin.value(),self.z_spin.value()); world_context=inspect_world(self.current.path); memory_context=self.memory.build_context(request,str(self.current.path)); combined=(world_context+"\n\n"+memory_context+"\n\nPLAYER BUILD PROTECTION="+str(self.settings.protect_player_builds))[:12000]
        self._thread=QThread(); self._worker=PlannerWorker(Planner(Ensemble(self.settings)),request,combined,center); self._worker.moveToThread(self._thread); self._thread.started.connect(self._worker.run); self._worker.activity.connect(self.activity.appendPlainText); self._worker.finished.connect(self._plan_finished); self._worker.failed.connect(self._plan_failed); self._worker.finished.connect(self._thread.quit); self._worker.failed.connect(self._thread.quit); self._thread.finished.connect(self._planning_cleanup); self._thread.start()

    def _plan_finished(self,result):
        self.last_plan=result.plan; self.plan_output.setPlainText(result.pretty()); self.preview.set_plan(self.last_plan); self.build_button.setEnabled(bool(self.last_plan.get("builds"))); self.activity.appendPlainText("WorldSmith • preview updated and plan is ready");
        try:self.memory.save_conversation(str(self.current.path),self.request.toPlainText(),str(self.last_plan.get("summary", "Plan generated")))
        except Exception: pass
        self.refresh_memory()

    def _plan_failed(self,message): self.activity.appendPlainText(f"WorldSmith • ERROR: {message}"); QMessageBox.critical(self,"Planning error",message)

    def _planning_cleanup(self): self.progress.hide(); self.plan_btn.setEnabled(True); self._worker=None; self._thread=None

    def build_plan(self):
        if not self.current or not self.last_plan:return
        try:
            self.close_editor(); backup=backup_world(self.current.path) if self.settings.auto_backup else None; self.editor=WorldEditor(self.current.path); self.editor.open(); self.activity.appendPlainText("Builder • writing blocks to save"); result=WorldBuilder(self.editor.require_level()).build(self.last_plan); self.editor.save(); self.close_editor(); msg=f"Built {result.blocks_changed} blocks, {result.roads_changed} road blocks, {result.systems_changed} redstone blocks."; self.activity.appendPlainText("Builder • world saved successfully")
            if backup: msg += f" Backup: {backup}"
            self.statusBar().showMessage(msg); self.build_button.setEnabled(False); QMessageBox.information(self,"WorldSmith",msg)
        except Exception as exc: self.close_editor(); QMessageBox.critical(self,"Build error",str(exc))

    def refresh_memory(self):
        if not hasattr(self,'memory_list'):return
        self.memory_list.clear()
        for memory in self.memory.list():
            item=QListWidgetItem(f"[{memory.kind}] {memory.content}"); item.setData(Qt.UserRole,memory.id); self.memory_list.addItem(item)

    def add_memory(self):
        text=self.memory_input.toPlainText().strip()
        if not text:return
        self.memory.remember(text,"user",str(self.current.path) if self.current else None); self.memory_input.clear(); self.refresh_memory(); self.statusBar().showMessage("Memory saved locally")

    def forget_memory(self):
        item=self.memory_list.currentItem()
        if not item:return
        self.memory.forget(int(item.data(Qt.UserRole))); self.refresh_memory()

    def choose_google_secret(self):
        path,_=QFileDialog.getOpenFileName(self,"Choose Google OAuth client JSON","","JSON files (*.json)")
        if path:self.google_secret_edit.setText(path); self.save_settings()

    def google_signin(self):
        self.save_settings()
        try:
            profile=GoogleAuth(Path(self.settings.google_client_secret)).sign_in(); self.settings.google_name=profile.get('name',''); self.settings.google_email=profile.get('email',''); self.settings.save(self.settings_path); self._refresh_provider_status(); self.statusBar().showMessage(f"Signed in as {self.settings.google_email}")
        except GoogleAuthError as exc: QMessageBox.warning(self,"Google sign-in",str(exc))
        except Exception as exc: QMessageBox.critical(self,"Google sign-in",str(exc))

    def google_signout(self):
        GoogleAuth(Path(self.settings.google_client_secret)).sign_out(); self.settings.google_name=""; self.settings.google_email=""; self.settings.save(self.settings_path); self.account_chip.setText("Guest"); self.sidebar_account.setText("Not signed in"); self.statusBar().showMessage("Signed out")

    def close_editor(self):
        if self.editor:
            try:self.editor.close()
            except Exception: pass
            self.editor=None

    def closeEvent(self,event):
        self.close_editor()
        if self._thread:
            self._thread.quit(); self._thread.wait(1500)
        event.accept()


def main():
    fmt=QSurfaceFormat(); fmt.setRenderableType(QSurfaceFormat.OpenGL); fmt.setProfile(QSurfaceFormat.CompatibilityProfile); QSurfaceFormat.setDefaultFormat(fmt)
    app=QApplication(sys.argv); app.setApplicationName("WorldSmith AI"); app.setOrganizationName("WorldSmith")
    window=WorldSmithWindow(); window.show(); return app.exec()
