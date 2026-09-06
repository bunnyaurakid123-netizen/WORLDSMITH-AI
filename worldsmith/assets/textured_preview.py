from __future__ import annotations

from PySide6.QtGui import QImage
from PySide6.QtOpenGL import QOpenGLTexture

from worldsmith.aaa import LiveWorldPreview
from worldsmith.assets.appearance import BlockAppearanceCache

try:
    from OpenGL import GL
except ImportError:  # pragma: no cover
    GL = None


class TexturedLiveWorldPreview(LiveWorldPreview):
    """Live preview with Minecraft/resource-pack textures and volumetric terrain columns."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.appearance_cache = BlockAppearanceCache()
        self.texture_cache: dict[str, QOpenGLTexture] = {}
        self._texture_failed: set[str] = set()

    def _texture_for(self, material: str):
        if GL is None:
            return None
        appearance = self.appearance_cache.resolve(material)
        texture_id = appearance.texture_id
        if not texture_id:
            return None
        if texture_id in self.texture_cache:
            return self.texture_cache[texture_id]
        if texture_id in self._texture_failed:
            return None
        try:
            raw = self.appearance_cache.catalog.texture_bytes(texture_id)
            image = QImage.fromData(raw or b"")
            if image.isNull():
                self._texture_failed.add(texture_id)
                return None
            image = image.convertToFormat(QImage.Format_RGBA8888).mirrored()
            texture = QOpenGLTexture(image)
            texture.setMinificationFilter(QOpenGLTexture.LinearMipMapLinear)
            texture.setMagnificationFilter(QOpenGLTexture.Linear)
            texture.setWrapMode(QOpenGLTexture.Repeat)
            self.texture_cache[texture_id] = texture
            return texture
        except Exception:
            self._texture_failed.add(texture_id)
            return None

    def _draw_column(self, x: float, top: float, z: float, bottom: float, half_size: float, material: str):
        appearance = self.appearance_cache.resolve(material)
        texture = self._texture_for(material)
        x0, x1 = x - half_size, x + half_size
        z0, z1 = z - half_size, z + half_size
        y0, y1 = bottom, top

        # Minecraft texture on the top face.
        if texture is not None:
            texture.bind()
            GL.glColor4f(1.0, 1.0, 1.0, 1.0)
            GL.glBegin(GL.GL_QUADS)
            GL.glTexCoord2f(0.0, 0.0); GL.glVertex3f(x0, y1, z0)
            GL.glTexCoord2f(1.0, 0.0); GL.glVertex3f(x1, y1, z0)
            GL.glTexCoord2f(1.0, 1.0); GL.glVertex3f(x1, y1, z1)
            GL.glTexCoord2f(0.0, 1.0); GL.glVertex3f(x0, y1, z1)
            GL.glEnd()
            texture.release()
        else:
            r, g, b = appearance.color
            GL.glColor3f(r, g, b)
            GL.glBegin(GL.GL_QUADS)
            GL.glVertex3f(x0, y1, z0); GL.glVertex3f(x1, y1, z0)
            GL.glVertex3f(x1, y1, z1); GL.glVertex3f(x0, y1, z1)
            GL.glEnd()

        # Directionally shaded side faces create actual volumetric terrain.
        base = appearance.color
        for shade, vertices in [
            (0.78, (x0, y0, z0, x1, y0, z0, x1, y1, z0, x0, y1, z0)),
            (0.62, (x1, y0, z0, x1, y0, z1, x1, y1, z1, x1, y1, z0)),
            (0.55, (x1, y0, z1, x0, y0, z1, x0, y1, z1, x1, y1, z1)),
            (0.70, (x0, y0, z1, x0, y0, z0, x0, y1, z0, x0, y1, z1)),
        ]:
            GL.glColor3f(base[0] * shade, base[1] * shade, base[2] * shade)
            GL.glBegin(GL.GL_QUADS)
            for i in range(0, 12, 3):
                GL.glVertex3f(vertices[i], vertices[i + 1], vertices[i + 2])
            GL.glEnd()

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
        floor = min_h - max(3.0, (max_h - min_h) * 0.35)

        for x, z, y, material in points:
            rx = (x - center[0]) * scale / max(1.0, step)
            rz = (z - center[2]) * scale / max(1.0, step)
            ry = ((y - (min_h + max_h) * 0.5) / max(1.0, max_h - min_h)) * 70.0
            bottom = ((floor - (min_h + max_h) * 0.5) / max(1.0, max_h - min_h)) * 70.0
            self._draw_column(rx, ry, rz, bottom, 1.25, material)
