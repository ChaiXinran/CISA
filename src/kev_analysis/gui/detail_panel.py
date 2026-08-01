"""Selected-CVE details."""

from PyQt6.QtWidgets import QFormLayout, QGroupBox, QLabel, QTextBrowser


class DetailPanel(QGroupBox):
    def __init__(self, parent=None) -> None:
        super().__init__("CVE 详情", parent)
        self.name, self.due_date, self.cwes = QLabel("未选择记录"), QLabel("—"), QLabel("—")
        self.name.setWordWrap(True)
        self.description, self.action, self.notes = QTextBrowser(), QTextBrowser(), QTextBrowser()
        for browser in (self.description, self.action, self.notes):
            browser.setMaximumHeight(110)
        layout = QFormLayout(self)
        for label, widget in (
            ("漏洞名称", self.name), ("简短描述", self.description), ("处置要求", self.action),
            ("截止日期", self.due_date), ("CWE", self.cwes), ("备注", self.notes),
        ):
            layout.addRow(label, widget)

    def clear_record(self) -> None:
        self.name.setText("未选择记录")
        self.description.clear(); self.action.clear(); self.notes.clear()
        self.due_date.setText("—"); self.cwes.setText("—")

    def set_record(self, record: dict) -> None:
        self.name.setText(str(record.get("vulnerabilityName", "")))
        self.description.setPlainText(str(record.get("shortDescription", "")))
        self.action.setPlainText(str(record.get("requiredAction", "")))
        self.due_date.setText(str(record.get("dueDate", "")))
        cwes = record.get("cwes", [])
        self.cwes.setText(", ".join(cwes) if isinstance(cwes, list) and cwes else "未提供")
        self.notes.setPlainText(str(record.get("notes", "")))
