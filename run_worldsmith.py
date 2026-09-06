from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from worldsmith.aaa import AAAWorldSmithWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("WorldSmith AI")
    app.setOrganizationName("WorldSmith")
    window = AAAWorldSmithWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
