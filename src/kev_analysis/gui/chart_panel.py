"""Filter-linked GUI dashboard containing the globe and analytical charts."""

from __future__ import annotations

import os
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd
import plotly.graph_objects as go
from PyQt6.QtCore import QUrl, pyqtSignal
from PyQt6.QtWidgets import QComboBox, QLabel, QVBoxLayout, QWidget
from PyQt6.QtWebEngineWidgets import QWebEngineView

from kev_analysis.analysis.cwe import build_cwe_summary, explode_cwes
from kev_analysis.analysis.vendor import build_vendor_summary
from .chart_export import export_widget_png
from .globe_view import (
    aggregate_vendor_locations, build_globe_figure,
    load_vendor_locations,
)
from .web_bridge import WebBridge, configure_channel, write_plotly_page


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

    vendors = build_vendor_summary(filtered_df).sort_values("count")
    vendor_figure = go.Figure(go.Bar(
        x=vendors["count"], y=vendors["vendor_clean"], orientation="h",
        customdata=vendors["vendor_clean"], marker_color="#2b7a78",
        hovertemplate="%{y}<br>记录：%{x}<extra></extra>",
    ))
    vendor_figure.update_layout(
        title="当前筛选结果的全部厂商",
        xaxis_title="记录数",
        height=max(560, 34 * len(vendors) + 110),
    )

    exploded = explode_cwes(filtered_df)
    cwes = build_cwe_summary(exploded, len(filtered_df)).sort_values("cve_count")
    cwe_figure = go.Figure(go.Bar(
        x=cwes["cve_count"], y=cwes["cwe"], orientation="h", marker_color="#b85c38",
        hovertemplate="%{y}<br>唯一 CVE：%{x}<extra></extra>",
    ))
    cwe_figure.update_layout(
        title="当前筛选结果的全部 CWE",
        xaxis_title="唯一 CVE 数",
        height=max(560, 34 * len(cwes) + 110),
    )
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
        self._headless = os.environ.get("QT_QPA_PLATFORM", "").lower() == "offscreen"
        self._temporary = TemporaryDirectory(prefix="kev_charts_")
        self._web_directory = Path(self._temporary.name)
        self._pages: dict[str, Path] = {}
        self.status = QLabel("尚未加载筛选结果")
        self.selector = QComboBox()
        for title, key in (
            ("3D 地球", "globe"), ("月度趋势", "monthly"),
            ("全部厂商", "vendor"), ("全部 CWE", "cwe"),
        ):
            self.selector.addItem(title, key)
        self.locations = load_vendor_locations()
        self.web = None
        self.placeholder = None
        if self._headless:
            self.placeholder = QLabel("无头测试模式不启动 WebEngine")
            self.placeholder.setWordWrap(True)
        else:
            self.web = QWebEngineView()
            self.bridge = WebBridge(self)
            self._bridge_connection = configure_channel(self.web, self.bridge)
            self.bridge.vendor_selected.connect(self._on_vendor_selected)
        self.selector.currentIndexChanged.connect(self._show_selected)
        layout = QVBoxLayout(self)
        layout.addWidget(self.status)
        layout.addWidget(self.selector)
        layout.addWidget(self.placeholder if self._headless else self.web, 1)

    def _on_vendor_selected(self, vendor: str) -> None:
        self.status.setText(f"地球上已选择厂商：{vendor}")
        self.vendor_selected.emit(vendor)

    def update_data(self, filtered_df: pd.DataFrame) -> None:
        self._data = filtered_df.copy(deep=True)
        mapped, mapping = aggregate_vendor_locations(self._data, self.locations)
        self.status.setText(
            f"当前筛选结果：{len(self._data):,} 条；已映射 {mapping['mapped_records']:,} 条，"
            f"未映射 {mapping['unmapped_records']:,} 条。位置仅表示厂商总部。"
        )
        figures = build_linked_figures(self._data)
        if not self._headless:
            all_figures = {"globe": build_globe_figure(mapped), **figures}
            self._pages = {}
            for name, figure in all_figures.items():
                self._pages[name] = write_plotly_page(
                    figure, self._web_directory, f"{name}.html",
                    click_customdata=name in {"globe", "vendor"},
                    adaptive_3d_markers=name == "globe",
                    vertical_scroll=name in {"vendor", "cwe"},
                )
            self._show_selected()
        self.export_available.emit(True)

    def _show_selected(self) -> None:
        if self._headless or not self._pages:
            return
        key = self.selector.currentData()
        page = self._pages.get(key)
        if page is not None:
            self.web.setUrl(QUrl.fromLocalFile(str(page)))

    def export_png(self, path: str | Path) -> None:
        export_widget_png(self.placeholder if self._headless else self.web, path)


ChartPanel = VisualizationPanel
