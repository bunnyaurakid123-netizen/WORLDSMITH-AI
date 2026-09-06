from __future__ import annotations

import math
import random

from PySide6.QtCore import QPoint, Qt
from PySide6.QtOpenGLWidgets import QOpenGLWidget

from worldsmith.preview_scene import PreviewScene

try:
    from OpenGL import GL
except ImportError:  # pragma: no cover
    GL = None


class Preview3D(QOpenGLWidget):
    """Interactive AAA-style planning viewport for WorldSmith's save-independent scene."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.plan: dict = {}
        self.scene = PreviewScene()
        self.yaw = -35.0
        self.pitch = 48.0
        self.zoom = 1.0
        self.pan_x = 0.0
        self.pan_y = -12.0
        self._last = QPoint()
        self._selected = -1
        self.setMinimumSize(700, 480)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setMouseTracking(True)

    def set_plan(self, plan: dict | None) -> None:
        self.plan = plan or {}
        self.scene.set_plan(self.plan)
        self._selected = -1
        self.update()

    def initializeGL(self):
        if GL is None:
            return
        GL.glClearColor(0.015, 0.022, 0.045, 1.0)
        GL.glEnable(GL.GL_DEPTH_TEST)
        GL.glDisable(GL.GL_CULL_FACE)
        GL.glEnable(GL.GL_BLEND)
        GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)
        GL.glShadeModel(GL.GL_SMOOTH)

    def resizeGL(self, width: int, height: int):
        if GL is None:
            return
        GL.glViewport(0, 0, max(1, width), max(1, height))
        GL.glMatrixMode(GL.GL_PROJECTION)
        GL.glLoadIdentity()
        aspect = max(1.0, width / max(1.0, float(height)))
        span = 145.0 / max(0.45, min(self.zoom, 3.5))
        GL.glOrtho(-span * aspect, span * aspect, -span, span, -1200, 1200)
        GL.glMatrixMode(GL.GL_MODELVIEW)

    def _terrain_height(self, x: float, z: float) -> float:
        vertices = self.scene.terrain_vertices()
        terrain = self.plan.get("terrain", {})
        radius = max(16.0, float(terrain.get("radius", 96)))
        if not vertices:
            return 0.0
        # Lightweight analytic fallback for roads/buildings between sampled points.
        seed = int(self.plan.get("seed", 1337))
        nx, nz = x / radius, z / radius
        fall = max(0.0, 1.0 - math.hypot(nx, nz) ** 3)
        macro = math.sin((x + seed % 97) / 23.0) * math.cos((z - seed % 71) / 31.0)
        detail = math.sin((x - z) / 67.0)
        return (0.48 + 0.28 * macro + 0.24 * detail) * fall * float(terrain.get("mountain_height", 80))

    def _quad(self, x: float, y: float, z: float, size: float):
        GL.glBegin(GL.GL_QUADS)
        GL.glVertex3f(x - size, y, z - size)
        GL.glVertex3f(x + size, y, z - size)
        GL.glVertex3f(x + size, y, z + size)
        GL.glVertex3f(x - size, y, z + size)
        GL.glEnd()

    def _box(self, x, y, z, w, d, h, alpha=0.88):
        x0, x1 = x - w / 2, x + w / 2
        z0, z1 = z - d / 2, z + d / 2
        y0, y1 = y, y + h
        GL.glColor4f(0.42, 0.60, 1.0, alpha)
        GL.glBegin(GL.GL_QUADS)
        faces = [
            ((x0,y0,z0),(x1,y0,z0),(x1,y0,z1),(x0,y0,z1)),
            ((x0,y1,z0),(x0,y1,z1),(x1,y1,z1),(x1,y1,z0)),
            ((x0,y0,z0),(x0,y1,z0),(x1,y1,z0),(x1,y0,z0)),
            ((x1,y0,z0),(x1,y1,z0),(x1,y1,z1),(x1,y0,z1)),
            ((x1,y0,z1),(x1,y1,z1),(x0,y1,z1),(x0,y0,z1)),
            ((x0,y0,z1),(x0,y1,z1),(x0,y1,z0),(x0,y0,z0)),
        ]
        for face in faces:
            for vx, vy, vz in face:
                GL.glVertex3f(vx, vy, vz)
        GL.glEnd()
        GL.glColor4f(0.70, 0.82, 1.0, 0.70)
        GL.glLineWidth(1.2)
        GL.glBegin(GL.GL_LINE_LOOP)
        GL.glVertex3f(x0,y0,z0); GL.glVertex3f(x1,y0,z0); GL.glVertex3f(x1,y0,z1); GL.glVertex3f(x0,y0,z1)
        GL.glEnd()
        GL.glBegin(GL.GL_LINE_LOOP)
        GL.glVertex3f(x0,y1,z0); GL.glVertex3f(x1,y1,z0); GL.glVertex3f(x1,y1,z1); GL.glVertex3f(x0,y1,z1)
        GL.glEnd()

    def _grid(self, radius: int):
        GL.glColor4f(0.25, 0.34, 0.55, 0.28)
        GL.glLineWidth(1.0)
        step = max(8, radius // 8)
        GL.glBegin(GL.GL_LINES)
        for p in range(-radius, radius + 1, step):
            GL.glVertex3f(-radius, 0, p); GL.glVertex3f(radius, 0, p)
            GL.glVertex3f(p, 0, -radius); GL.glVertex3f(p, 0, radius)
        GL.glEnd()

    def _axes(self):
        GL.glLineWidth(2.0)
        GL.glBegin(GL.GL_LINES)
        GL.glColor4f(0.8, 0.2, 0.2, 0.9); GL.glVertex3f(0,0,0); GL.glVertex3f(24,0,0)
        GL.glColor4f(0.2, 0.8, 0.3, 0.9); GL.glVertex3f(0,0,0); GL.glVertex3f(0,24,0)
        GL.glColor4f(0.2, 0.5, 1.0, 0.9); GL.glVertex3f(0,0,0); GL.glVertex3f(0,0,24)
        GL.glEnd()

    def paintGL(self):
        if GL is None:
            return
        GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
        GL.glMatrixMode(GL.GL_MODELVIEW)
        GL.glLoadIdentity()
        GL.glTranslatef(self.pan_x, self.pan_y, -250.0)
        GL.glRotatef(self.pitch, 1, 0, 0)
        GL.glRotatef(self.yaw, 0, 1, 0)

        terrain = self.plan.get("terrain", {})
        radius = max(16, min(int(terrain.get("radius", 96)), 192))
        mountain = max(8.0, float(terrain.get("mountain_height", 80)))
        vertices = self.scene.terrain_vertices()
        if vertices:
            rows = len(vertices)
            cols = len(vertices[0])
            for rz in range(rows - 1):
                GL.glBegin(GL.GL_TRIANGLE_STRIP)
                for rx in range(cols):
                    for row in (rz, rz + 1):
                        x, h, z = vertices[row][rx]
                        rel = max(0.0, min(1.0, (h + 5.0) / mountain))
                        if h > mountain * 0.72:
                            GL.glColor4f(0.72 + rel * 0.14, 0.76 + rel * 0.12, 0.84 + rel * 0.10, 1.0)
                        elif h < mountain * 0.10 and terrain.get("water", True):
                            GL.glColor4f(0.08, 0.28, 0.46, 0.95)
                        else:
                            GL.glColor4f(0.08 + rel * 0.10, 0.18 + rel * 0.23, 0.11 + rel * 0.13, 1.0)
                        GL.glVertex3f(x * 1.05, h * 1.05, z * 1.05)
                GL.glEnd()

        self._grid(radius)
        self._axes()

        if terrain.get("water", True):
            GL.glColor4f(0.05, 0.20, 0.34, 0.33)
            sea = mountain * 0.06
            GL.glBegin(GL.GL_QUADS)
            GL.glVertex3f(-radius, sea, -radius); GL.glVertex3f(radius, sea, -radius)
            GL.glVertex3f(radius, sea, radius); GL.glVertex3f(-radius, sea, radius)
            GL.glEnd()

        center = self.plan.get("center", [0, 100, 0])
        roads = self.plan.get("roads", [])
        GL.glColor4f(0.38, 0.28, 0.18, 1.0)
        for road in roads:
            x1 = float(road.get("x1", center[0]) - center[0]); z1 = float(road.get("z1", center[2]) - center[2])
            x2 = float(road.get("x2", center[0]) - center[0]); z2 = float(road.get("z2", center[2]) - center[2])
            width = max(1.0, min(6.0, float(road.get("width", 3))))
            steps = max(1, int(max(abs(x2-x1), abs(z2-z1)) / 3))
            for i in range(steps + 1):
                t = i / steps; x = x1 + (x2-x1) * t; z = z1 + (z2-z1) * t
                self._quad(x, self._terrain_height(x,z) + 1.0, z, width * 0.65)

        objects = self.scene.objects()
        rng = random.Random(int(self.plan.get("seed", 1337)))
        for index, build in enumerate(objects):
            bx, bz = float(build["x"]), float(build["z"])
            by = self._terrain_height(bx, bz) + 2.5
            w, d, h = build["width"], build["depth"], build["height"]
            kind = str(build["type"]).lower()
            if "castle" in kind or "fortress" in kind or "palace" in kind:
                GL.glColor4f(0.45, 0.52, 0.69, 0.95)
            elif "tower" in kind:
                GL.glColor4f(0.50, 0.34, 0.20, 0.95)
            elif "house" in kind or "tavern" in kind:
                c = 0.28 + rng.random() * 0.10
                GL.glColor4f(0.55, 0.38 + c * 0.1, 0.22, 0.95)
            else:
                GL.glColor4f(0.34, 0.48, 0.62, 0.92)
            self._box(bx, by, bz, w, d, h, 0.92)
            if index == self._selected:
                GL.glColor4f(0.95, 0.84, 0.25, 1.0)
                GL.glLineWidth(3.0)
                GL.glBegin(GL.GL_LINE_LOOP)
                GL.glVertex3f(bx-w/2, by-0.2, bz-d/2); GL.glVertex3f(bx+w/2, by-0.2, bz-d/2)
                GL.glVertex3f(bx+w/2, by-0.2, bz+d/2); GL.glVertex3f(bx-w/2, by-0.2, bz+d/2)
                GL.glEnd()

    def mousePressEvent(self, event):
        self._last = event.position().toPoint()
        if event.button() == Qt.LeftButton:
            self.setFocus()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        pos = event.position().toPoint(); dx = pos.x() - self._last.x(); dy = pos.y() - self._last.y()
        if event.buttons() & Qt.LeftButton:
            self.yaw += dx * 0.45; self.pitch = max(15.0, min(78.0, self.pitch + dy * 0.34))
        elif event.buttons() & Qt.RightButton:
            self.pan_x += dx * 0.15; self.pan_y -= dy * 0.15
        self._last = pos; self.update(); super().mouseMoveEvent(event)

    def wheelEvent(self, event):
        self.zoom *= 1.0 + (0.11 if event.angleDelta().y() > 0 else -0.11)
        self.zoom = max(0.45, min(3.5, self.zoom)); self.resizeGL(self.width(), self.height()); self.update()
