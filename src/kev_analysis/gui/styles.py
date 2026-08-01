"""High-contrast application stylesheet."""

APP_STYLESHEET = """
QMainWindow, QWidget#centralRoot {
    background: #f1f5f9;
    color: #172033;
    font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
    font-size: 14px;
}
QLabel, QGroupBox QLabel, QTabWidget QWidget, QFormLayout QLabel {
    color: #172033;
}
QFrame#topBar {
    background: #123247;
    border-radius: 10px;
}
QFrame#topBar QLabel { color: #cfe2ed; }
QFrame#topBar QLabel[role="value"] {
    color: white;
    font-size: 16px;
    font-weight: 700;
}
QPushButton {
    min-height: 34px;
    padding: 4px 14px;
    border-radius: 6px;
    border: 1px solid #9aabba;
    background: white;
    color: #18384b;
    font-weight: 600;
}
QPushButton:hover { background: #e8f2f6; border-color: #287492; }
QPushButton:pressed { background: #d5e8ef; }
QPushButton:disabled { background: #dce3e8; color: #8795a1; border-color: #c7d0d7; }
QPushButton#primaryButton {
    background: #e1533d;
    color: white;
    border: 1px solid #e1533d;
}
QPushButton#primaryButton:hover { background: #c9412e; }
QPushButton#exportButton {
    background: #167d8d;
    color: white;
    border: 1px solid #167d8d;
}
QPushButton#exportButton:hover { background: #106675; }
QLabel#loadStatus {
    padding: 5px 10px;
    border-radius: 10px;
    background: #64748b;
    color: white;
    font-weight: 700;
}
QLabel#loadStatus[state="loading"] { background: #d99418; color: #271b03; }
QLabel#loadStatus[state="success"] { background: #2f9e67; color: white; }
QLabel#loadStatus[state="error"] { background: #c53b42; color: white; }
QLabel#resultSummary {
    padding: 11px 16px;
    border-left: 5px solid #e1533d;
    border-radius: 5px;
    background: #dcecf2;
    color: #123247;
    font-size: 15px;
    font-weight: 700;
}
QGroupBox {
    margin-top: 12px;
    padding: 16px 10px 10px 10px;
    border: 1px solid #b9c9d4;
    border-radius: 8px;
    background: white;
    font-weight: 700;
    color: #123247;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: #176b82;
}
QLineEdit, QComboBox {
    min-height: 30px;
    padding: 3px 8px;
    border: 1px solid #aabac5;
    border-radius: 5px;
    background: #fbfdfe;
    color: #172033;
}
QComboBox QAbstractItemView {
    background: white;
    color: #172033;
    selection-background-color: #287e9a;
    selection-color: white;
}
QLineEdit:focus, QComboBox:focus { border: 2px solid #17839b; background: white; }
QTabWidget::pane { border: 1px solid #b9c9d4; background: white; border-radius: 6px; }
QTabBar::tab {
    padding: 10px 22px;
    margin-right: 3px;
    background: #d9e4ea;
    color: #294b5b;
    font-weight: 600;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
}
QTabBar::tab:selected { background: #176b82; color: white; }
QTableWidget {
    gridline-color: #d7e0e6;
    alternate-background-color: #eef4f7;
    background: white;
    selection-background-color: #287e9a;
    selection-color: white;
    border: none;
    color: #172033;
}
QHeaderView::section {
    padding: 8px;
    background: #183f54;
    color: white;
    border: 0;
    border-right: 1px solid #49697a;
    font-weight: 700;
}
QTextBrowser {
    border: 1px solid #c4d1d9;
    border-radius: 5px;
    background: #f8fbfc;
    color: #172033;
    padding: 4px;
}
QStatusBar { background: #183f54; color: white; padding-left: 8px; }
QSplitter::handle { background: #c6d4dc; width: 3px; }
"""
