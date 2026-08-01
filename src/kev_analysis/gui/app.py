"""GUI application entry point."""

import sys
from PyQt6.QtWidgets import QApplication
from .main_window import MainWindow


def run() -> int:
    application = QApplication.instance() or QApplication(sys.argv)
    application.setApplicationName("CISA KEV Analysis")
    window = MainWindow()
    window.show()
    return application.exec()
