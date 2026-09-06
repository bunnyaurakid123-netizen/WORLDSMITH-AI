from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

import worldsmith.app as app_module
from worldsmith.aaa import AAAWorldSmithWindow
from worldsmith.generation.advanced_builder import AdvancedWorldBuilder

# The AAA launcher upgrades the base app's generation pipeline without duplicating its UI.
app_module.WorldBuilder = AdvancedWorldBuilder


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("WorldSmith AI")
    app.setOrganizationName("WorldSmith")
    window = AAAWorldSmithWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
