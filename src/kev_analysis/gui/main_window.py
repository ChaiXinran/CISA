"""Main GUI composition and data-flow coordination."""

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtWidgets import (
    QFileDialog, QFrame, QGridLayout, QLabel, QMainWindow, QMessageBox, QPushButton,
    QSizePolicy, QSplitter, QStatusBar, QTabWidget, QVBoxLayout, QWidget,
)

from kev_analysis.analysis.queries import filter_kev
from kev_analysis.data import load_catalog, prepare_data, validate_catalog
from kev_analysis.data.prepare import serialize_cwes
from .detail_panel import DetailPanel
from .filter_panel import FilterPanel
from .results_table import ResultsTable
from .state import GuiState
from .chart_panel import VisualizationPanel
from .chart_export import export_widget_png, normalized_png_path
from .styles import APP_STYLESHEET


class MainWindow(QMainWindow):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.state = GuiState()
        self.setWindowTitle("CISA KEV 查询与可视化")
        self.resize(1440, 900)
        self.open_button = QPushButton("选择 KEV JSON")
        self.export_button = QPushButton("导出当前结果 CSV")
        self.export_chart_button = QPushButton("导出当前视图 PNG")
        self.open_button.setObjectName("primaryButton")
        self.export_button.setObjectName("exportButton")
        self.export_chart_button.setObjectName("exportButton")
        self.export_button.setEnabled(False)
        self.export_chart_button.setEnabled(False)
        self.catalog_version, self.release_date, self.record_count = QLabel("—"), QLabel("—"), QLabel("0")
        self.load_status = QLabel("未加载")
        self.load_status.setObjectName("loadStatus")
        self.load_status.setProperty("state", "idle")
        for value_label in (self.catalog_version, self.release_date, self.record_count):
            value_label.setProperty("role", "value")
        header = QGridLayout()
        for column, widget in enumerate((
            self.open_button, QLabel("目录版本"), self.catalog_version, QLabel("发布日期"),
            self.release_date, QLabel("记录数"), self.record_count,
            QLabel("状态"), self.load_status, self.export_button, self.export_chart_button,
        )):
            header.addWidget(widget, 0, column)
        top_bar = QFrame()
        top_bar.setObjectName("topBar")
        top_bar.setLayout(header)
        top_bar.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        top_bar.setFixedHeight(82)
        self.filters, self.visualizations = FilterPanel(), VisualizationPanel()
        self.results, self.details = ResultsTable(), DetailPanel()
        self.result_summary = QLabel("当前结果：0 条 · 厂商：0 · 产品：0 · Known：0")
        self.result_summary.setObjectName("resultSummary")
        self.result_summary.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.result_summary.setFixedHeight(44)
        self.result_split = QSplitter(Qt.Orientation.Horizontal)
        self.result_split.addWidget(self.results); self.result_split.addWidget(self.details)
        self.result_split.setStretchFactor(0, 3); self.result_split.setStretchFactor(1, 2)
        self.tabs = QTabWidget()
        self.tabs.addTab(self.visualizations, "可视化")
        self.tabs.addTab(self.result_split, "CVE 结果与详情")
        content = QSplitter(Qt.Orientation.Horizontal)
        content.addWidget(self.filters); content.addWidget(self.tabs)
        content.setStretchFactor(1, 1)
        root, layout = QWidget(), QVBoxLayout()
        root.setObjectName("centralRoot")
        root.setLayout(layout); layout.addWidget(top_bar); layout.addWidget(self.result_summary); layout.addWidget(content)
        layout.setStretch(2, 1)
        self.setCentralWidget(root); self.setStatusBar(QStatusBar())
        self.setStyleSheet(APP_STYLESHEET)
        self.statusBar().showMessage("请选择课程 JSON 文件")
        self.open_button.clicked.connect(self.choose_file)
        self.export_button.clicked.connect(self.export_results)
        self.export_chart_button.clicked.connect(self.export_chart)
        self.filters.apply_requested.connect(self.apply_filters)
        self.filters.reset_requested.connect(self.reset_filters)
        self.results.cve_selected.connect(self.show_cve)
        self.visualizations.export_available.connect(self.export_chart_button.setEnabled)
        self.visualizations.vendor_selected.connect(self.apply_vendor_from_visualization)
        self.tabs.currentChanged.connect(self._update_export_view_label)
        self._update_export_view_label()
        self._install_shortcuts()

    def _install_shortcuts(self) -> None:
        for text, shortcut, callback in (
            ("打开", QKeySequence.StandardKey.Open, self.choose_file),
            ("导出", QKeySequence.StandardKey.Save, self.export_results),
            ("重置筛选", QKeySequence("Ctrl+R"), self.filters.reset),
        ):
            action = QAction(text, self)
            action.setShortcut(shortcut)
            action.triggered.connect(callback)
            self.addAction(action)

    def choose_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "选择 CISA KEV JSON", "", "JSON (*.json)")
        if path:
            self.load_path(path)

    def load_path(self, path: str | Path) -> bool:
        self._set_load_status("加载中…", "loading")
        self.statusBar().showMessage(f"正在加载：{path}")
        try:
            metadata, raw = load_catalog(path)
            validation = validate_catalog(metadata, raw)
            if not validation.passed:
                raise ValueError(f"数据验证未通过：{', '.join(validation.errors)}")
            prepared = prepare_data(raw)
        except Exception as exc:
            QMessageBox.critical(self, "加载失败", str(exc))
            self._set_load_status("加载失败", "error")
            self.statusBar().showMessage("加载失败")
            return False
        self.state = GuiState(metadata, raw, prepared, prepared.copy(deep=True))
        self.catalog_version.setText(str(metadata.get("catalogVersion", "—")))
        self.release_date.setText(str(metadata.get("dateReleased", "—"))[:10])
        self.record_count.setText(f"{len(prepared):,}")
        self._set_load_status("验证通过", "success")
        self.filters.setEnabled(True)
        self.export_button.setEnabled(True)
        self._publish_filtered_data()
        self.statusBar().showMessage(f"已加载并验证 {len(prepared):,} 条记录")
        return True

    def _set_load_status(self, text: str, state: str) -> None:
        self.load_status.setText(text)
        self.load_status.setProperty("state", state)
        self.load_status.style().unpolish(self.load_status)
        self.load_status.style().polish(self.load_status)

    def apply_filters(self, values: dict) -> None:
        if not self.state.loaded:
            QMessageBox.information(self, "尚未加载", "请先选择课程 JSON 文件。")
            return
        try:
            result, _ = filter_kev(self.state.prepared_df, **values)
        except (ValueError, TypeError) as exc:
            QMessageBox.warning(self, "筛选条件无效", str(exc))
            return
        self.state.filtered_df, self.state.active_filters = result, values.copy()
        self.state.selected_cve = None
        self._publish_filtered_data()
        self.statusBar().showMessage(f"当前筛选结果：{len(result):,} 条")

    def reset_filters(self) -> None:
        if self.state.loaded:
            self.state.filtered_df = self.state.prepared_df.copy(deep=True)
            self.state.active_filters, self.state.selected_cve = {}, None
            self._publish_filtered_data()
            self.statusBar().showMessage(f"筛选已重置：{len(self.state.filtered_df):,} 条")

    def _publish_filtered_data(self) -> None:
        self.results.update_data(self.state.filtered_df)
        self.visualizations.update_data(self.state.filtered_df)
        self.details.clear_record()
        data = self.state.filtered_df
        known = int(data["knownRansomwareCampaignUse"].eq("Known").sum()) if not data.empty else 0
        self.result_summary.setText(
            f"当前结果：{len(data):,} 条 · 厂商：{data['vendor_clean'].nunique():,} · "
            f"产品：{data['product_clean'].nunique():,} · Known：{known:,}"
        )

    def show_cve(self, cve_id: str) -> None:
        match = self.state.filtered_df.loc[self.state.filtered_df["cveID"].eq(cve_id)]
        if not match.empty:
            self.state.selected_cve = cve_id
            self.details.set_record(match.iloc[0].to_dict())

    def apply_vendor_from_visualization(self, vendor: str) -> None:
        """Apply a globe-selected vendor through the existing filter pipeline."""
        if not self.state.loaded:
            return
        self.filters.vendor.setText(vendor)
        self.apply_filters(self.filters.values())
        self.statusBar().showMessage(f"已从地球选择厂商：{vendor}")

    def export_results(self) -> None:
        if not self.state.loaded:
            return
        path, _ = QFileDialog.getSaveFileName(self, "导出当前筛选结果", "kev_filtered.csv", "CSV (*.csv)")
        if path:
            self.export_to_path(path)

    def export_chart(self) -> None:
        if not self.state.loaded:
            return
        visual = self.tabs.currentWidget() is self.visualizations
        title = "导出当前可视化" if visual else "导出当前 CVE 结果表"
        default_name = "kev_visualization.png" if visual else "kev_results_table.png"
        path, _ = QFileDialog.getSaveFileName(self, title, default_name, "PNG (*.png)")
        if path:
            self.export_chart_to_path(path)

    def export_chart_to_path(self, path: str | Path) -> Path:
        """Export the currently visible visualization or results/details view."""
        if not self.state.loaded:
            raise RuntimeError("尚未加载 KEV 数据")
        destination = normalized_png_path(path)
        visual = self.tabs.currentWidget() is self.visualizations
        try:
            if visual:
                self.visualizations.export_png(destination)
            else:
                export_widget_png(self.results, destination)
        except (OSError, PermissionError) as exc:
            QMessageBox.critical(self, "图表导出失败", str(exc))
            raise
        view_name = "当前可视化" if visual else "当前 CVE 结果表"
        self.statusBar().showMessage(f"已导出{view_name}：{destination}")
        return destination

    def _update_export_view_label(self) -> None:
        visual = self.tabs.currentWidget() is self.visualizations
        self.export_chart_button.setText(
            "导出当前图表 PNG" if visual else "导出当前表格 PNG"
        )

    def export_to_path(self, path: str | Path) -> Path:
        """Export current rows; separate from the dialog so it is testable."""
        if not self.state.loaded:
            raise RuntimeError("尚未加载 KEV 数据")
        destination = Path(path)
        if destination.suffix.lower() != ".csv":
            destination = destination.with_suffix(".csv")
        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            exported = self.state.filtered_df.copy(deep=True)
            exported["cwes"] = exported["cwes"].map(serialize_cwes)
            exported.to_csv(destination, index=False, encoding="utf-8-sig", date_format="%Y-%m-%d")
        except (OSError, PermissionError) as exc:
            QMessageBox.critical(self, "导出失败", str(exc))
            raise
        self.statusBar().showMessage(f"已导出 {len(exported):,} 条记录：{destination}")
        return destination
