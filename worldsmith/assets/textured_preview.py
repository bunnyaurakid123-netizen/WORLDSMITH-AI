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
    """Live preview that uses discovered Minecraft/resource-pack textures when available."""

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
            image = QImage.fromData(self.appearance_cache.catalog.texture_bytes(texture_id) or b"")
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

        GL.glEnable(GL.GL_TEXTURE_2D)
        for x, z, y, material in points:
            rx = (x - center[0]) * scale / max(1.0, step)
            rz = (z - center[2]) * scale / max(1.0, step)
            ry = ((y - (min_h + max_h) * 0.5) / max(1.0, max_h - min_h)) * 70.0
            texture = self._texture_for(material)
            if texture is not None:
                texture.bind()
                GL.glColor4f(1.0, 1.0, 1.0, 1.0)
                GL.glBegin(GL.GL_QUADS)
                s = 1.25
                GL.glTexCoord2f(0.0, 0.0); GL.glVertex3f(rx - s, ry, rz - s)
                GL.glTexCoord2f(1.0, 0.0); GL.glVertex3f(rx + s, ry, rz - s)
                GL.glTexCoord2f(1.0, 1.0); GL.glVertex3f(rx + s, ry, rz + s)
                GL.glTexCoord2f(0.0, 1.0); GL.glVertex3f(rx - s, ry, rz + s)
                GL.glEnd()
                texture.release()
            else:
                r, g, b = self.appearance_cache.resolve(material).color
                GL.glColor3f(r, g, b)
                GL.glBegin(GL.GL_QUADS)
                s = 1.25
                GL.glVertex3f(rx - s, ry, rz - s); GL.glVertex3f(rx + s, ry, rz - s)
                GL.glVertex3f(rx + s, ry, rz + s); GL.glVertex3f(rx - s, ry, rz + s)
                GL.glEnd()
        GL.glDisable(GL.GL_TEXTURE_2D)
