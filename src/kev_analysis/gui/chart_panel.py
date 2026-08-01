"""Filter-linked GUI dashboard containing the globe and analytical charts."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd
import plotly.graph_objects as go
from PyQt6.QtCore import QUrl, pyqtSignal
from PyQt6.QtWidgets import QLabel, QTabWidget, QVBoxLayout, QWidget
from PyQt6.QtWebEngineWidgets import QWebEngineView

from kev_analysis.analysis.cwe import build_cwe_summary, explode_cwes
from kev_analysis.analysis.vendor import build_vendor_summary
from .chart_export import export_widget_png
from .globe_view import GlobeView
from .web_bridge import write_plotly_page


def build_linked_figures(filtered_df: pd.DataFrame) -> dict[str, go.Figure]:
    """Build month, vendor and CWE figures from exactly the current rows."""
    required = {"date_added", "vendor_clean", "knownRansomwareCampaignUse", "cwes", "cveID"}
    missing = sorted(required.difference(filtered_df.columns))
    if missing:
        raise KeyError(f"filtered_df 缺少字段：{missing}")

    monthly = (
        filtered_df.assign(month=filtered_df["date_added"].dt.strftime("%Y-%m"))
        .groupby("month", as_index=False).size().rename(columns={"size": "count"})
    )
    month_figure = go.Figure(go.Scatter(
        x=monthly["month"], y=monthly["count"], mode="lines+markers",
        line={"color": "#1f596e", "width": 3},
    ))
    month_figure.update_layout(title="当前筛选结果的月度 KEV 加入记录", xaxis_title="月份", yaxis_title="记录数")

    vendors = build_vendor_summary(filtered_df).head(20).sort_values("count")
    vendor_figure = go.Figure(go.Bar(
        x=vendors["count"], y=vendors["vendor_clean"], orientation="h",
        customdata=vendors["vendor_clean"], marker_color="#2b7a78",
        hovertemplate="%{y}<br>记录：%{x}<extra></extra>",
    ))
    vendor_figure.update_layout(title="当前筛选结果 Top 20 厂商标签", xaxis_title="记录数")

    exploded = explode_cwes(filtered_df)
    cwes = build_cwe_summary(exploded, len(filtered_df)).head(20).sort_values("cve_count")
    cwe_figure = go.Figure(go.Bar(
        x=cwes["cve_count"], y=cwes["cwe"], orientation="h", marker_color="#b85c38",
        hovertemplate="%{y}<br>唯一 CVE：%{x}<extra></extra>",
    ))
    cwe_figure.update_layout(title="当前筛选结果 Top 20 CWE", xaxis_title="唯一 CVE 数")
    for figure in (month_figure, vendor_figure, cwe_figure):
        figure.update_layout(margin={"l": 70, "r": 30, "t": 60, "b": 55}, paper_bgcolor="#f7f9fb")
    return {"monthly": month_figure, "vendor": vendor_figure, "cwe": cwe_figure}


class VisualizationPanel(QWidget):
    """B-line component ready for A to place in the visualization tab."""

    export_available = pyqtSignal(bool)
    vendor_selected = pyqtSignal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._data = pd.DataFrame()
        self._temporary = TemporaryDirectory(prefix="kev_charts_")
        self._web_directory = Path(self._temporary.name)
        self.status = QLabel("尚未加载筛选结果")
        self.tabs = QTabWidget()
        self.globe = GlobeView()
        self.web_views = {name: QWebEngineView() for name in ("monthly", "vendor", "cwe")}
        self.tabs.addTab(self.globe, "3D 地球")
        self.tabs.addTab(self.web_views["monthly"], "月度趋势")
        self.tabs.addTab(self.web_views["vendor"], "厂商 Top 20")
        self.tabs.addTab(self.web_views["cwe"], "CWE Top 20")
        self.globe.vendor_selected.connect(self._on_vendor_selected)
        layout = QVBoxLayout(self)
        layout.addWidget(self.status)
        layout.addWidget(self.tabs, 1)

    def _on_vendor_selected(self, vendor: str) -> None:
        self.status.setText(f"地球上已选择厂商：{vendor}")
        self.vendor_selected.emit(vendor)

    def update_data(self, filtered_df: pd.DataFrame) -> None:
        self._data = filtered_df.copy(deep=True)
        self.status.setText(f"当前筛选结果：{len(self._data):,} 条；所有图表使用同一份 filtered_df。")
        self.globe.update_data(self._data)
        figures = build_linked_figures(self._data)
        for name, figure in figures.items():
            page = write_plotly_page(figure, self._web_directory, f"{name}.html")
            self.web_views[name].setUrl(QUrl.fromLocalFile(str(page)))
        self.export_available.emit(True)

    def export_png(self, path: str | Path) -> None:
        export_widget_png(self.tabs.currentWidget(), path)


ChartPanel = VisualizationPanel
