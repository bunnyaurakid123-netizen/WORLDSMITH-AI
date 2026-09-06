from __future__ import annotations

import math
import random

from PySide6.QtCore import Qt, QPoint
from PySide6.QtOpenGLWidgets import QOpenGLWidget

try:
    from OpenGL import GL
except ImportError:  # pragma: no cover - handled by dependency installation
    GL = None


class Preview3D(QOpenGLWidget):
    """Lightweight interactive terrain preview generated from a WorldSmith plan."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.plan: dict = {}
        self.yaw = -35.0
        self.pitch = 42.0
        self.zoom = 1.0
        self._last = QPoint()
        self.setMinimumSize(520, 360)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setMouseTracking(True)

    def set_plan(self, plan: dict) -> None:
        self.plan = plan or {}
        self.update()

    def initializeGL(self):
        if GL is None:
            return
        GL.glClearColor(0.025, 0.04, 0.08, 1.0)
        GL.glEnable(GL.GL_DEPTH_TEST)
        GL.glDisable(GL.GL_CULL_FACE)

    def resizeGL(self, width: int, height: int):
        if GL is None:
            return
        GL.glViewport(0, 0, max(1, width), max(1, height))
        GL.glMatrixMode(GL.GL_PROJECTION)
        GL.glLoadIdentity()
        aspect = max(1.0, width / max(1.0, float(height)))
        span = 130.0 / max(0.5, min(self.zoom, 3.0))
        GL.glOrtho(-span * aspect, span * aspect, -span, span, -700, 700)
        GL.glMatrixMode(GL.GL_MODELVIEW)

    def _height(self, x: float, z: float) -> float:
        terrain = self.plan.get("terrain", {})
        radius = max(16.0, float(terrain.get("radius", 96)))
        mountain = max(8.0, float(terrain.get("mountain_height", 80)))
        rough = max(0.25, float(terrain.get("roughness", 1.0)))
        nx, nz = x / radius, z / radius
        macro = math.sin(nx * 2.4) * math.cos(nz * 1.7)
        ridged = 1.0 - abs(math.sin(nx * 5.8 + 0.7) * math.cos(nz * 4.9 - 0.2))
        detail = math.sin(nx * 13.0 + nz * 4.0) * math.cos(nz * 12.0)
        mountain_mask = max(0.0, macro * 0.8 + 0.2)
        return (mountain_mask * ridged * 0.75 + detail * 0.08) * mountain * rough

    def paintGL(self):
        if GL is None:
            return
        GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
        GL.glMatrixMode(GL.GL_MODELVIEW)
        GL.glLoadIdentity()
        GL.glTranslatef(0.0, -12.0, -240.0)
        GL.glRotatef(self.pitch, 1, 0, 0)
        GL.glRotatef(self.yaw, 0, 1, 0)
        GL.glScalef(1.0, 1.0, 1.0)

        plan = self.plan
        terrain = plan.get("terrain", {})
        radius = max(16, min(int(terrain.get("radius", 96)), 192))
        step = max(4, radius // 18)
        scale = 1.15

        # Terrain surface as a triangle mesh. The preview is intentionally lightweight.
        for z in range(-radius, radius, step):
            GL.glBegin(GL.GL_TRIANGLE_STRIP)
            for x in range(-radius, radius + step, step):
                for zz in (z, z + step):
                    h = self._height(x, zz)
                    shade = max(0.0, min(1.0, (h + 35.0) / 115.0))
                    GL.glColor3f(0.10 + shade * 0.18, 0.22 + shade * 0.30, 0.16 + shade * 0.22)
                    GL.glVertex3f(x * scale, h * scale, zz * scale)
            GL.glEnd()

        # Highlight planned structures as simple ghost volumes.
        builds = plan.get("builds", [])[:24]
        rng = random.Random(17)
        for b in builds:
            bx = float(b.get("x", 0) - plan.get("center", [0, 100, 0])[0])
            bz = float(b.get("z", 0) - plan.get("center", [0, 100, 0])[2])
            by = self._height(bx, bz) + 8
            w = max(3, min(30, float(b.get("width", 10))))
            d = max(3, min(30, float(b.get("depth", 10))))
            h = max(4, min(40, float(b.get("height", 10))))
            c = 0.45 + (rng.random() * 0.2)
            GL.glColor4f(0.35, 0.55, 1.0, c)
            GL.glBegin(GL.GL_LINES)
            for sx in (-w, w):
                for sz in (-d, d):
                    GL.glVertex3f((bx + sx) * scale, by * scale, (bz + sz) * scale)
                    GL.glVertex3f((bx + sx) * scale, (by + h) * scale, (bz + sz) * scale)
            GL.glEnd()

    def mousePressEvent(self, event):
        self._last = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        pos = event.position().toPoint()
        if event.buttons() & Qt.LeftButton:
            dx = pos.x() - self._last.x()
            dy = pos.y() - self._last.y()
            self.yaw += dx * 0.45
            self.pitch = max(15.0, min(75.0, self.pitch + dy * 0.35))
            self.update()
        self._last = pos
        super().mouseMoveEvent(event)

    def wheelEvent(self, event):
        self.zoom *= 1.0 + (0.10 if event.angleDelta().y() > 0 else -0.10)
        self.zoom = max(0.55, min(2.5, self.zoom))
        self.resizeGL(self.width(), self.height())
        self.update()
