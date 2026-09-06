from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

import worldsmith.app as app_module
from worldsmith.aaa import AAAWorldSmithWindow
from worldsmith.async_build import build_plan_async
from worldsmith.generation.advanced_builder import AdvancedWorldBuilder

# AAA launcher upgrades the base app's builder and moves build execution off the GUI thread.
app_module.WorldBuilder = AdvancedWorldBuilder
AAAWorldSmithWindow.build_plan = build_plan_async


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("WorldSmith AI")
    app.setOrganizationName("WorldSmith")
    window = AAAWorldSmithWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
