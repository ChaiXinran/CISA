"""CVE result table."""

import pandas as pd
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QAbstractItemView, QTableWidget, QTableWidgetItem

DISPLAY_COLUMNS = [
    ("cveID", "CVE"), ("vendorProject", "厂商/项目"), ("product", "产品"),
    ("dateAdded", "加入日期"), ("dueDate", "截止日期"),
    ("knownRansomwareCampaignUse", "勒索软件状态"),
]


class ResultsTable(QTableWidget):
    cve_selected = pyqtSignal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setColumnCount(len(DISPLAY_COLUMNS))
        self.setHorizontalHeaderLabels([label for _, label in DISPLAY_COLUMNS])
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setAlternatingRowColors(True)
        self.verticalHeader().setVisible(False)
        self.itemSelectionChanged.connect(self._emit_selection)

    def update_data(self, df: pd.DataFrame) -> None:
        self.setUpdatesEnabled(False)
        self.blockSignals(True)
        self.clearContents()
        self.setRowCount(len(df))
        for row_index, record in enumerate(df.to_dict(orient="records")):
            for column_index, (field, _) in enumerate(DISPLAY_COLUMNS):
                item = QTableWidgetItem(str(record.get(field, "")))
                if field == "cveID":
                    item.setData(Qt.ItemDataRole.UserRole, record.get("cveID"))
                    item.setForeground(QColor("#126d86"))
                elif field == "knownRansomwareCampaignUse":
                    if record.get(field) == "Known":
                        item.setBackground(QColor("#ffd9d4"))
                        item.setForeground(QColor("#9b261d"))
                    else:
                        item.setBackground(QColor("#e6edf2"))
                        item.setForeground(QColor("#405564"))
                self.setItem(row_index, column_index, item)
        self.resizeColumnsToContents()
        self.blockSignals(False)
        self.setUpdatesEnabled(True)

    def _emit_selection(self) -> None:
        selected = self.selectedItems()
        if selected:
            item = self.item(selected[0].row(), 0)
            if item is not None:
                self.cve_selected.emit(str(item.data(Qt.ItemDataRole.UserRole)))
