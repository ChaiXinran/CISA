"""Stable visualization contract for parallel development."""

from pathlib import Path

import pandas as pd
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget


class VisualizationPanel(QWidget):
    export_available = pyqtSignal(bool)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._data = pd.DataFrame()
        self.label = QLabel("可视化接口已就绪\n等待接入 3D 地球、月度趋势和 CWE 图表")
        self.label.setWordWrap(True)
        self.label.setStyleSheet("font-size:18px;color:#52606d;padding:36px")
        layout = QVBoxLayout(self)
        layout.addWidget(self.label)

    def update_data(self, filtered_df: pd.DataFrame) -> None:
        self._data = filtered_df.copy(deep=True)
        self.label.setText(f"当前筛选结果：{len(filtered_df):,} 条\n可视化组件接口已就绪")
        self.export_available.emit(False)

    def export_png(self, path: str | Path) -> None:
        raise NotImplementedError("占位组件尚未提供 PNG 导出")
