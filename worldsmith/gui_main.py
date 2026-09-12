from __future__ import annotations

from PySide6.QtWidgets import QApplication
from .aaa import AAAWorldSmithWindow
from .project_ui import install_project_menu
from .generation.advanced_builder import AdvancedWorldBuilder
from . import app as app_module
from . import aaa as aaa_module
from .assets.appearance import BlockAppearanceCache
from .assets.textured_preview import TexturedLiveWorldPreview
from .async_build import build_plan_async

# GUI is the primary application entry point; reuse the mature editor/3D systems.
app_module.WorldBuilder = AdvancedWorldBuilder
AAAWorldSmithWindow.build_plan = build_plan_async
aaa_module.LiveWorldPreview = TexturedLiveWorldPreview
_cache = BlockAppearanceCache()
TexturedLiveWorldPreview._material_color = staticmethod(lambda material: _cache.resolve(material).color)


def main() -> int:
    app = QApplication.instance() or QApplication([])
    app.setApplicationName("WorldSmith AI")
    app.setOrganizationName("WorldSmith")
    window = AAAWorldSmithWindow()
    install_project_menu(window)
    window.show()
    return app.exec()
