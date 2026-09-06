from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

import worldsmith.app as app_module
from worldsmith.aaa import AAAWorldSmithWindow, LiveWorldPreview
from worldsmith.assets.appearance import BlockAppearanceCache
from worldsmith.async_build import build_plan_async
from worldsmith.generation.advanced_builder import AdvancedWorldBuilder

# AAA launcher upgrades the base app's builder and moves build execution off the GUI thread.
app_module.WorldBuilder = AdvancedWorldBuilder
AAAWorldSmithWindow.build_plan = build_plan_async

# Use locally installed Minecraft/resource-pack assets for viewport appearance when available.
_appearance_cache = BlockAppearanceCache()
LiveWorldPreview._material_color = staticmethod(lambda material: _appearance_cache.resolve(material).color)


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("WorldSmith AI")
    app.setOrganizationName("WorldSmith")
    window = AAAWorldSmithWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
