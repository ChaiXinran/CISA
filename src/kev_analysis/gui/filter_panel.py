"""Filter controls without data-processing logic."""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QComboBox, QFormLayout, QGroupBox, QHBoxLayout, QLineEdit, QPushButton, QVBoxLayout


class FilterPanel(QGroupBox):
    apply_requested = pyqtSignal(dict)
    reset_requested = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__("组合筛选", parent)
        self.start_date = QLineEdit(placeholderText="YYYY-MM-DD")
        self.end_date = QLineEdit(placeholderText="YYYY-MM-DD")
        self.vendor = QLineEdit(placeholderText="大小写不敏感")
        self.product = QLineEdit(placeholderText="产品关键词")
        self.ransomware = QComboBox()
        self.ransomware.addItems(["全部", "Known", "Unknown"])
        self.cwe = QLineEdit(placeholderText="例如 CWE-79")
        form = QFormLayout()
        for label, widget in (
            ("开始日期", self.start_date), ("结束日期", self.end_date),
            ("厂商/项目", self.vendor), ("产品", self.product),
            ("勒索软件状态", self.ransomware), ("CWE", self.cwe),
        ):
            form.addRow(label, widget)
        apply_button, reset_button = QPushButton("应用筛选"), QPushButton("重置")
        self.apply_button, self.reset_button = apply_button, reset_button
        self.apply_button.setObjectName("primaryButton")
        apply_button.clicked.connect(lambda: self.apply_requested.emit(self.values()))
        reset_button.clicked.connect(self.reset)
        buttons = QHBoxLayout()
        buttons.addWidget(apply_button)
        buttons.addWidget(reset_button)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addLayout(buttons)
        self.setEnabled(False)

    @staticmethod
    def _optional(text: str) -> str | None:
        return text.strip() or None

    def values(self) -> dict:
        status = self.ransomware.currentText()
        return {
            "start_date": self._optional(self.start_date.text()),
            "end_date": self._optional(self.end_date.text()),
            "vendor": self._optional(self.vendor.text()),
            "product": self._optional(self.product.text()),
            "ransomware": None if status == "全部" else status,
            "cwe": self._optional(self.cwe.text()),
        }

    def reset(self) -> None:
        for widget in (self.start_date, self.end_date, self.vendor, self.product, self.cwe):
            widget.clear()
        self.ransomware.setCurrentIndex(0)
        self.reset_requested.emit()
