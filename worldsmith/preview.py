from __future__ import annotations

import math
import random

from PySide6.QtCore import QPoint, Qt
from PySide6.QtOpenGLWidgets import QOpenGLWidget

try:
    from OpenGL import GL
except ImportError:  # pragma: no cover
    GL = None

from worldsmith.generation.noise import fbm, ridge


class Preview3D(QOpenGLWidget):
    """Interactive, lightweight preview of WorldSmith's actual procedural plan."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.plan: dict = {}
        self.yaw = -35.0
        self.pitch = 48.0
        self.zoom = 1.0
        self.pan_x = 0.0
        self.pan_y = -12.0
        self._last = QPoint()
        self.setMinimumSize(560, 400)
        self.setFocusPolicy(Qt.StrongFocus)

    def set_plan(self, plan: dict) -> None:
        self.plan = plan or {}
        self.update()

    def initializeGL(self):
        if GL is None:
            return
        GL.glClearColor(0.018, 0.026, 0.055, 1.0)
        GL.glEnable(GL.GL_DEPTH_TEST)
        GL.glDisable(GL.GL_CULL_FACE)
        GL.glShadeModel(GL.GL_SMOOTH)

    def resizeGL(self, width: int, height: int):
        if GL is None:
            return
        GL.glViewport(0, 0, max(1, width), max(1, height))
        GL.glMatrixMode(GL.GL_PROJECTION)
        GL.glLoadIdentity()
        aspect = max(1.0, width / max(1.0, float(height)))
        span = 145.0 / max(0.45, min(self.zoom, 3.5))
        GL.glOrtho(-span * aspect, span * aspect, -span, span, -900, 900)
        GL.glMatrixMode(GL.GL_MODELVIEW)

    def _terrain_height(self, x: float, z: float) -> float:
        terrain = self.plan.get("terrain", {})
        radius = max(16.0, float(terrain.get("radius", 96)))
        mountain = max(8.0, float(terrain.get("mountain_height", 80)))
        rough = max(0.3, float(terrain.get("roughness", 1.0)))
        macro = fbm(x / 180.0, z / 180.0, int(self.plan.get("seed", 1337)) + 11, 5)
        continent = fbm(x / 420.0, z / 420.0, int(self.plan.get("seed", 1337)) + 23, 4)
        r = ridge(x / 78.0, z / 78.0, int(self.plan.get("seed", 1337)) + 37)
        detail = fbm(x / 24.0, z / 24.0, int(self.plan.get("seed", 1337)) + 71, 4)
        nx, nz = x / radius, z / radius
        falloff = max(0.0, 1.0 - (math.hypot(nx, nz) ** 3))
        raw = max(0.0, (0.30 + continent * 0.76 + macro * 0.44) * 0.42 + (r * r) * 0.46 + detail * 0.18)
        return (raw * falloff) * mountain * rough

    def _quad(self, x: float, y: float, z: float, size: float):
        GL.glBegin(GL.GL_QUADS)
        GL.glVertex3f(x - size, y, z - size)
        GL.glVertex3f(x + size, y, z - size)
        GL.glVertex3f(x + size, y, z + size)
        GL.glVertex3f(x - size, y, z + size)
        GL.glEnd()

    def _box(self, x, y, z, w, d, h):
        x0, x1 = x - w / 2, x + w / 2
        z0, z1 = z - d / 2, z + d / 2
        y0, y1 = y, y + h
        GL.glBegin(GL.GL_QUADS)
        for a, b, c, d_, e, f in (
            (x0, y0, z0, x1, y0, z0),
            (x1, y0, z0, x1, y0, z1),
            (x1, y0, z1, x0, y0, z1),
            (x0, y0, z1, x0, y0, z0),
        ):
            GL.glVertex3f(a, b, c); GL.glVertex3f(d_, e, f)
        GL.glVertex3f(x0, y1, z0); GL.glVertex3f(x1, y1, z0); GL.glVertex3f(x1, y0, z0); GL.glVertex3f(x0, y0, z0)
        GL.glVertex3f(x1, y1, z0); GL.glVertex3f(x1, y1, z1); GL.glVertex3f(x1, y0, z1); GL.glVertex3f(x1, y0, z0)
        GL.glVertex3f(x1, y1, z1); GL.glVertex3f(x0, y1, z1); GL.glVertex3f(x0, y0, z1); GL.glVertex3f(x1, y0, z1)
        GL.glVertex3f(x0, y1, z1); GL.glVertex3f(x0, y1, z0); GL.glVertex3f(x0, y0, z0); GL.glVertex3f(x0, y0, z1)
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

        plan = self.plan
        terrain = plan.get("terrain", {})
        radius = max(16, min(int(terrain.get("radius", 96)), 128))
        step = max(4, radius // 22)
        scale = 1.08
        seed = int(plan.get("seed", 1337))

        # Terrain mesh. The same height field is used by the generation engine.
        for z in range(-radius, radius, step):
            GL.glBegin(GL.GL_TRIANGLE_STRIP)
            for x in range(-radius, radius + step, step):
                for zz in (z, z + step):
                    h = self._terrain_height(x, zz)
                    shade = max(0.0, min(1.0, (h + 8.0) / max(1.0, float(terrain.get("mountain_height", 80)))))
                    if h < 5 and terrain.get("water", True):
                        GL.glColor3f(0.08, 0.25, 0.38)
                    elif h > float(terrain.get("mountain_height", 80)) * 0.72:
                        GL.glColor3f(0.78 + shade * 0.08, 0.82 + shade * 0.06, 0.88 + shade * 0.05)
                    else:
                        GL.glColor3f(0.09 + shade * 0.09, 0.22 + shade * 0.24, 0.13 + shade * 0.12)
                    GL.glVertex3f(x * scale, h * scale, zz * scale)
            GL.glEnd()

        # Water highlight plane.
        if terrain.get("water", True):
            GL.glColor3f(0.07, 0.24, 0.36)
            sea = 4.5
            GL.glBegin(GL.GL_QUADS)
            GL.glVertex3f(-radius * scale, sea, -radius * scale)
            GL.glVertex3f(radius * scale, sea, -radius * scale)
            GL.glVertex3f(radius * scale, sea, radius * scale)
            GL.glVertex3f(-radius * scale, sea, radius * scale)
            GL.glEnd()

        # Roads.
        GL.glColor3f(0.36, 0.29, 0.20)
        for road in plan.get("roads", []):
            x1 = float(road.get("x1", 0) - plan.get("center", [0, 100, 0])[0])
            z1 = float(road.get("z1", 0) - plan.get("center", [0, 100, 0])[2])
            x2 = float(road.get("x2", 0) - plan.get("center", [0, 100, 0])[0])
            z2 = float(road.get("z2", 0) - plan.get("center", [0, 100, 0])[2])
            width = max(1.0, min(5.0, float(road.get("width", 3))))
            steps = max(1, int(max(abs(x2-x1), abs(z2-z1)) / 3))
            for i in range(steps + 1):
                t = i / steps
                x = x1 + (x2 - x1) * t
                z = z1 + (z2 - z1) * t
                self._quad(x * scale, self._terrain_height(x, z) * scale + 0.8, z * scale, width * 0.75)

        # Planned structures.
        center = plan.get("center", [0, 100, 0])
        rng = random.Random(seed)
        for build in plan.get("builds", [])[:24]:
            bx = float(build.get("x", center[0]) - center[0])
            bz = float(build.get("z", center[2]) - center[2])
            w = max(5.0, min(64.0, float(build.get("width", 10))))
            d = max(5.0, min(64.0, float(build.get("depth", 10))))
            h = max(5.0, min(70.0, float(build.get("height", 10))))
            by = self._terrain_height(bx, bz) + 3
            kind = str(build.get("type", "house")).lower()
            if kind in {"castle", "fortress", "palace", "keep"}:
                GL.glColor3f(0.55, 0.60, 0.72)
            elif kind in {"tower", "watchtower"}:
                GL.glColor3f(0.62, 0.48, 0.30)
            else:
                GL.glColor3f(0.45 + rng.random() * 0.08, 0.34 + rng.random() * 0.07, 0.23)
            self._box(bx * scale, by * scale, bz * scale, w * scale, d * scale, h * scale)
            # Roof ridge marker.
            GL.glColor3f(0.22, 0.16, 0.12)
            GL.glBegin(GL.GL_LINES)
            GL.glVertex3f((bx - w * 0.35) * scale, (by + h) * scale, bz * scale)
            GL.glVertex3f((bx + w * 0.35) * scale, (by + h) * scale, bz * scale)
            GL.glEnd()

    def mousePressEvent(self, event):
        self._last = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        pos = event.position().toPoint()
        dx = pos.x() - self._last.x()
        dy = pos.y() - self._last.y()
        if event.buttons() & Qt.LeftButton:
            self.yaw += dx * 0.45
            self.pitch = max(15.0, min(78.0, self.pitch + dy * 0.34))
        elif event.buttons() & Qt.RightButton:
            self.pan_x += dx * 0.15
            self.pan_y -= dy * 0.15
        self._last = pos
        self.update()
        super().mouseMoveEvent(event)

    def wheelEvent(self, event):
        self.zoom *= 1.0 + (0.11 if event.angleDelta().y() > 0 else -0.11)
        self.zoom = max(0.45, min(3.5, self.zoom))
        self.resizeGL(self.width(), self.height())
        self.update()
