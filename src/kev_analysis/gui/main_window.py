"""Main GUI composition and data-flow coordination."""

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFileDialog, QGridLayout, QLabel, QMainWindow, QMessageBox, QPushButton,
    QSplitter, QStatusBar, QTabWidget, QVBoxLayout, QWidget,
)

from kev_analysis.analysis.queries import filter_kev
from kev_analysis.data import load_catalog, prepare_data, validate_catalog
from kev_analysis.data.prepare import serialize_cwes
from .detail_panel import DetailPanel
from .filter_panel import FilterPanel
from .results_table import ResultsTable
from .state import GuiState
from .visualization_panel import VisualizationPanel


class MainWindow(QMainWindow):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.state = GuiState()
        self.setWindowTitle("CISA KEV 查询与可视化")
        self.resize(1440, 900)
        self.open_button, self.export_button = QPushButton("选择 KEV JSON"), QPushButton("导出当前结果 CSV")
        self.export_button.setEnabled(False)
        self.catalog_version, self.release_date, self.record_count = QLabel("—"), QLabel("—"), QLabel("0")
        header = QGridLayout()
        for column, widget in enumerate((
            self.open_button, QLabel("目录版本"), self.catalog_version, QLabel("发布日期"),
            self.release_date, QLabel("记录数"), self.record_count, self.export_button,
        )):
            header.addWidget(widget, 0, column)
        self.filters, self.visualizations = FilterPanel(), VisualizationPanel()
        self.results, self.details = ResultsTable(), DetailPanel()
        result_split = QSplitter(Qt.Orientation.Horizontal)
        result_split.addWidget(self.results); result_split.addWidget(self.details)
        result_split.setStretchFactor(0, 3); result_split.setStretchFactor(1, 2)
        tabs = QTabWidget()
        tabs.addTab(self.visualizations, "可视化")
        tabs.addTab(result_split, "CVE 结果与详情")
        content = QSplitter(Qt.Orientation.Horizontal)
        content.addWidget(self.filters); content.addWidget(tabs)
        content.setStretchFactor(1, 1)
        root, layout = QWidget(), QVBoxLayout()
        root.setLayout(layout); layout.addLayout(header); layout.addWidget(content)
        self.setCentralWidget(root); self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("请选择课程 JSON 文件")
        self.open_button.clicked.connect(self.choose_file)
        self.export_button.clicked.connect(self.export_results)
        self.filters.apply_requested.connect(self.apply_filters)
        self.filters.reset_requested.connect(self.reset_filters)
        self.results.cve_selected.connect(self.show_cve)

    def choose_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "选择 CISA KEV JSON", "", "JSON (*.json)")
        if path:
            self.load_path(path)

    def load_path(self, path: str | Path) -> None:
        try:
            metadata, raw = load_catalog(path)
            validation = validate_catalog(metadata, raw)
            if not validation.passed:
                raise ValueError(f"数据验证未通过：{', '.join(validation.errors)}")
            prepared = prepare_data(raw)
        except Exception as exc:
            QMessageBox.critical(self, "加载失败", str(exc))
            self.statusBar().showMessage("加载失败")
            return
        self.state = GuiState(metadata, raw, prepared, prepared.copy(deep=True))
        self.catalog_version.setText(str(metadata.get("catalogVersion", "—")))
        self.release_date.setText(str(metadata.get("dateReleased", "—"))[:10])
        self.record_count.setText(f"{len(prepared):,}")
        self.export_button.setEnabled(True)
        self._publish_filtered_data()
        self.statusBar().showMessage(f"已加载并验证 {len(prepared):,} 条记录")

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

    def show_cve(self, cve_id: str) -> None:
        match = self.state.filtered_df.loc[self.state.filtered_df["cveID"].eq(cve_id)]
        if not match.empty:
            self.state.selected_cve = cve_id
            self.details.set_record(match.iloc[0].to_dict())

    def export_results(self) -> None:
        if not self.state.loaded:
            return
        path, _ = QFileDialog.getSaveFileName(self, "导出当前筛选结果", "kev_filtered.csv", "CSV (*.csv)")
        if path:
            exported = self.state.filtered_df.copy(deep=True)
            exported["cwes"] = exported["cwes"].map(serialize_cwes)
            exported.to_csv(path, index=False, encoding="utf-8-sig", date_format="%Y-%m-%d")
            self.statusBar().showMessage(f"已导出 {len(exported):,} 条记录：{path}")
