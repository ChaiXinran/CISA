"""GUI application entry point."""

import sys
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from .main_window import MainWindow


def run(initial_path: str | Path | None = None) -> int:
    application = QApplication.instance() or QApplication(sys.argv)
    application.setApplicationName("CISA KEV Analysis")
    window = MainWindow()
    if initial_path is not None:
        window.load_path(initial_path)
    window.show()
    return application.exec()
