from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

import worldsmith.aaa as aaa_module
import worldsmith.app as app_module
from worldsmith.aaa import AAAWorldSmithWindow
from worldsmith.assets.appearance import BlockAppearanceCache
from worldsmith.assets.textured_preview import TexturedLiveWorldPreview
from worldsmith.async_build import build_plan_async
from worldsmith.generation.advanced_builder import AdvancedWorldBuilder
from worldsmith.project_ui import install_project_menu


# Install the AAA pipeline once for all supported launch paths.
app_module.WorldBuilder = AdvancedWorldBuilder
AAAWorldSmithWindow.build_plan = build_plan_async
aaa_module.LiveWorldPreview = TexturedLiveWorldPreview
_appearance_cache = BlockAppearanceCache()
TexturedLiveWorldPreview._material_color = staticmethod(lambda material: _appearance_cache.resolve(material).color)


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("WorldSmith AI")
    app.setOrganizationName("WorldSmith")
    window = AAAWorldSmithWindow()
    install_project_menu(window)
    window.show()
    return app.exec()
