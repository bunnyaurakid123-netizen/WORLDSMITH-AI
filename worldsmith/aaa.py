from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QPoint, QThread, Qt, Signal
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtWidgets import (
    QComboBox,
    QDockWidget,
    QDoubleSpinBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from worldsmith.app import WorldSmithWindow
from worldsmith.backup import backup_world
from worldsmith.editor.operations import Selection, VoxelEditor

try:
    from OpenGL import GL
except ImportError:  # pragma: no cover
    GL = None


class LiveWorldScanWorker(QObject):
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, level, center: tuple[int, int, int], radius: int = 32, step: int = 4):
        super().__init__()
        self.level = level
        self.center = center
        self.radius = max(8, min(int(radius), 48))
        self.step = max(2, min(int(step), 8))

    @staticmethod
    def _is_air(block) -> bool:
        text = str(block).lower()
        return "air" in text or text.endswith(":void")

    def run(self):
        try:
            wrapper = getattr(self.level, "level_wrapper", None)
            version = getattr(wrapper, "max_world_version", getattr(wrapper, "version", (1, 20, 4)))
            platform = getattr(wrapper, "platform", "java")
            version_key = (platform, version)
            cx, cy, cz = self.center
            min_y, max_y = -64, 320
            points: list[tuple[int, int, str]] = []
            for x in range(cx - self.radius, cx + self.radius + 1, self.step):
                for z in range(cz - self.radius, cz + self.radius + 1, self.step):
                    top = min_y
                    material = "minecraft:air"
                    for y in range(max_y, min_y - 1, -4):
                        block, _ = self.level.get_version_block(x, y, z, "minecraft:overworld", version_key)
                        if not self._is_air(block):
                            top = y
                            material = str(block)
                            break
                    points.append((x, z, top, material))
            self.finished.emit({"center": self.center, "radius": self.radius, "step": self.step, "points": points})
        except Exception as exc:
            self.failed.emit(str(exc))


class LiveWorldPreview(QOpenGLWidget):
    """Lightweight live terrain view sampled from the actual opened save."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.snapshot = None
        self.yaw = -35.0
        self.pitch = 48.0
        self.zoom = 1.0
        self.pan_x = 0.0
        self.pan_y = -20.0
        self._last = QPoint()
        self.setMinimumSize(600, 420)

    def set_snapshot(self, snapshot):
        self.snapshot = snapshot
        self.update()

    def initializeGL(self):
        if GL is None:
            return
        GL.glClearColor(0.015, 0.02, 0.04, 1.0)
        GL.glEnable(GL.GL_DEPTH_TEST)

    def resizeGL(self, w, h):
        if GL is None:
            return
        GL.glViewport(0, 0, max(1, w), max(1, h))
        GL.glMatrixMode(GL.GL_PROJECTION)
        GL.glLoadIdentity()
        aspect = max(1.0, w / max(1.0, float(h)))
        span = 105.0 / max(0.4, min(self.zoom, 3.5))
        GL.glOrtho(-span * aspect, span * aspect, -span, span, -900, 900)
        GL.glMatrixMode(GL.GL_MODELVIEW)

    @staticmethod
    def _material_color(material: str):
        value = material.lower()
        if "snow" in value or "ice" in value:
            return 0.82, 0.88, 0.96
        if "stone" in value or "deepslate" in value or "andesite" in value:
            return 0.38, 0.40, 0.44
        if "sand" in value or "sandstone" in value:
            return 0.72, 0.61, 0.39
        if "water" in value:
            return 0.10, 0.35, 0.56
        if "wood" in value or "log" in value or "plank" in value:
            return 0.46, 0.29, 0.15
        if "grass" in value or "leaves" in value or "moss" in value:
            return 0.16, 0.40, 0.18
        return 0.32, 0.30, 0.27

    def paintGL(self):
        if GL is None:
            return
        GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
        if not self.snapshot:
            return
        GL.glMatrixMode(GL.GL_MODELVIEW)
        GL.glLoadIdentity()
        GL.glTranslatef(self.pan_x, self.pan_y, -220.0)
        GL.glRotatef(self.pitch, 1, 0, 0)
        GL.glRotatef(self.yaw, 0, 1, 0)
        center = self.snapshot["center"]
        points = self.snapshot["points"]
        max_h = max((p[2] for p in points), default=center[1])
        min_h = min((p[2] for p in points), default=center[1])
        scale = 1.6
        step = float(self.snapshot["step"])
        for x, z, y, material in points:
            rx, rz = (x - center[0]) * scale / max(1.0, step), (z - center[2]) * scale / max(1.0, step)
            ry = ((y - (min_h + max_h) * 0.5) / max(1.0, max_h - min_h)) * 70.0
            r, g, b = self._material_color(material)
            GL.glColor3f(r, g, b)
            GL.glBegin(GL.GL_QUADS)
            s = 1.25
            GL.glVertex3f(rx - s, ry, rz - s); GL.glVertex3f(rx + s, ry, rz - s)
            GL.glVertex3f(rx + s, ry, rz + s); GL.glVertex3f(rx - s, ry, rz + s)
            GL.glEnd()

    def mousePressEvent(self, event):
        self._last = event.position().toPoint()

    def mouseMoveEvent(self, event):
        pos = event.position().toPoint()
        dx, dy = pos.x() - self._last.x(), pos.y() - self._last.y()
        if event.buttons() & Qt.LeftButton:
            self.yaw += dx * 0.45
            self.pitch = max(15.0, min(80.0, self.pitch + dy * 0.34))
        elif event.buttons() & Qt.RightButton:
            self.pan_x += dx * 0.14
            self.pan_y -= dy * 0.14
        self._last = pos
        self.update()

    def wheelEvent(self, event):
        self.zoom *= 1.1 if event.angleDelta().y() > 0 else 0.9
        self.zoom = max(0.4, min(3.5, self.zoom))
        self.resizeGL(self.width(), self.height())
        self.update()


class VoxelToolsPanel(QWidget):
    status = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.editor: VoxelEditor | None = None
        self.world_path: Path | None = None
        self.preview: LiveWorldPreview | None = None
        self._backup_created = False
        self._scan_thread = None
        self._scan_worker = None

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)

        selection_box = QGroupBox("Selection")
        grid = QGridLayout(selection_box)
        self.coords: dict[str, QSpinBox] = {}
        for row, axis in enumerate(("X1", "Y1", "Z1", "X2", "Y2", "Z2")):
            box = QSpinBox(); box.setRange(-30_000_000, 30_000_000)
            self.coords[axis] = box
            grid.addWidget(QLabel(axis), row // 3, (row % 3) * 2)
            grid.addWidget(box, row // 3, (row % 3) * 2 + 1)
        root.addWidget(selection_box)

        form = QFormLayout()
        self.block = QComboBox()
        self.block.setEditable(True)
        self.block.addItems(["stone", "stone_bricks", "spruce", "oak", "deepslate", "grass", "glass", "quartz", "air"])
        form.addRow("Block", self.block)
        self.brush = QComboBox(); self.brush.addItems(["Fill", "Hollow"]); form.addRow("Selection brush", self.brush)
        self.radius = QSpinBox(); self.radius.setRange(1, 64); self.radius.setValue(4); form.addRow("Radius", self.radius)
        self.height = QSpinBox(); self.height.setRange(1, 128); self.height.setValue(8); form.addRow("Height", self.height)
        root.addLayout(form)

        actions = QGridLayout()
        for text, fn, row, col in [
            ("Set selection", self.apply_selection, 0, 0),
            ("Sphere", self.apply_sphere, 0, 1),
            ("Cylinder", self.apply_cylinder, 1, 0),
            ("Undo", self.do_undo, 1, 1),
            ("Redo", self.do_redo, 2, 0),
            ("Save world", self.save_world, 2, 1),
        ]:
            button = QPushButton(text); button.clicked.connect(fn); actions.addWidget(button, row, col)
        root.addLayout(actions)
        root.addStretch()
        self.info = QLabel("Open a world to enable voxel editing.")
        self.info.setWordWrap(True)
        root.addWidget(self.info)

    def set_preview(self, preview: LiveWorldPreview):
        self.preview = preview

    def set_world(self, level, path: Path):
        self.editor = VoxelEditor(level)
        self.world_path = Path(path)
        self._backup_created = False
        self.info.setText(f"Voxel tools active for {self.world_path.name}")
        self.scan_preview(level)

    def clear_world(self):
        self.editor = None; self.world_path = None; self._backup_created = False
        self.info.setText("Open a world to enable voxel editing.")

    def selection(self) -> Selection:
        return Selection(*(self.coords[k].value() for k in ("X1", "Y1", "Z1", "X2", "Y2", "Z2")))

    def _before_edit(self):
        if self.editor is None or self.world_path is None:
            raise RuntimeError("Open a world first")
        if not self._backup_created:
            backup_world(self.world_path)
            self._backup_created = True

    def apply_selection(self):
        try:
            self._before_edit(); self.editor.select(self.selection())
            result = self.editor.hollow_selection(self.block.currentText()) if self.brush.currentText() == "Hollow" else self.editor.fill_selection(self.block.currentText())
            self.status.emit(f"Voxel brush changed {result.changed} blocks")
        except Exception as exc:
            QMessageBox.critical(self, "Voxel edit", str(exc))

    def apply_sphere(self):
        try:
            self._before_edit(); s = self.selection(); center = ((s.x1 + s.x2) // 2, (s.y1 + s.y2) // 2, (s.z1 + s.z2) // 2)
            result = self.editor.sphere_at(center, self.radius.value(), self.block.currentText())
            self.status.emit(f"Sphere brush changed {result.changed} blocks")
        except Exception as exc:
            QMessageBox.critical(self, "Voxel edit", str(exc))

    def apply_cylinder(self):
        try:
            self._before_edit(); s = self.selection(); center = ((s.x1 + s.x2) // 2, s.y1, (s.z1 + s.z2) // 2)
            result = self.editor.cylinder_at(center, self.radius.value(), self.height.value(), self.block.currentText())
            self.status.emit(f"Cylinder brush changed {result.changed} blocks")
        except Exception as exc:
            QMessageBox.critical(self, "Voxel edit", str(exc))

    def do_undo(self):
        if not self.editor: return
        self.status.emit(f"Undo changed {self.editor.undo()} blocks")

    def do_redo(self):
        if not self.editor: return
        self.status.emit(f"Redo changed {self.editor.redo()} blocks")

    def save_world(self):
        self.status.emit("Use WorldSmith's world save flow after reviewing changes.")

    def scan_preview(self, level):
        if self.preview is None:
            return
        center = tuple(self.coords[k].value() for k in ("X1", "Y1", "Z1"))
        self._scan_thread = QThread(); self._scan_worker = LiveWorldScanWorker(level, center)
        self._scan_worker.moveToThread(self._scan_thread)
        self._scan_thread.started.connect(self._scan_worker.run)
        self._scan_worker.finished.connect(self.preview.set_snapshot)
        self._scan_worker.failed.connect(lambda message: self.status.emit(f"Live scan failed: {message}"))
        self._scan_worker.finished.connect(self._scan_thread.quit); self._scan_worker.failed.connect(self._scan_thread.quit)
        self._scan_thread.start()


class AAAWorldSmithWindow(WorldSmithWindow):
    """WorldSmith main window with the live voxel editing dock enabled."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("WorldSmith AI — AAA World Studio")
        self.live_preview = LiveWorldPreview()
        self.tools = VoxelToolsPanel()
        self.tools.set_preview(self.live_preview)
        self.tools.status.connect(self.statusBar().showMessage)

        self.preview_dock = QDockWidget("Live Voxel Editor", self)
        dock_widget = QWidget()
        dock_layout = QVBoxLayout(dock_widget)
        dock_layout.setContentsMargins(0, 0, 0, 0)
        dock_layout.addWidget(self.live_preview, 1)
        dock_layout.addWidget(self.tools)
        self.preview_dock.setWidget(dock_widget)
        self.preview_dock.setAllowedAreas(Qt.RightDockWidgetArea | Qt.BottomDockWidgetArea)
        self.addDockWidget(Qt.RightDockWidgetArea, self.preview_dock)

        self._refresh_aaa_state()

    def open_selected(self):
        super().open_selected()
        if self.editor and self.current:
            self.tools.set_world(self.editor.require_level(), self.current.path)
            self._refresh_aaa_state()

    def close_editor(self):
        self.tools.clear_world() if hasattr(self, "tools") else None
        super().close_editor()

    def _refresh_aaa_state(self):
        self.statusBar().showMessage("AAA editor ready — select a world to load live voxel tools")
