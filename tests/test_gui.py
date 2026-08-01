import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pandas as pd
import pytest
from PyQt6.QtWidgets import QApplication
from kev_analysis.gui.main_window import MainWindow


@pytest.fixture(scope="module")
def application():
    return QApplication.instance() or QApplication([])


def test_gui_load_filter_reset_details_and_export(application, tmp_path):
    root = Path(__file__).resolve().parents[1]
    window = MainWindow()
    assert window.load_path(root / "data/CISA_KEV_2026-07-29.json")
    assert window.state.loaded and len(window.state.filtered_df) == 1656
    assert window.catalog_version.text() == "2026.07.29"
    assert window.load_status.text() == "验证通过"
    assert window.filters.isEnabled()
    assert window.export_chart_button.isEnabled()
    window.apply_filters({
        "start_date": None, "end_date": None, "vendor": "Microsoft",
        "product": None, "ransomware": "Known", "cwe": None,
    })
    assert not window.state.filtered_df.empty
    assert window.state.filtered_df["vendor_clean"].str.contains("Microsoft", case=False).all()
    assert window.state.filtered_df["knownRansomwareCampaignUse"].eq("Known").all()
    assert "Known" in window.result_summary.text()
    window.visualizations.vendor_selected.emit("Cisco")
    assert window.filters.vendor.text() == "Cisco"
    assert window.state.filtered_df["vendor_clean"].str.contains("Cisco", case=False).all()
    cve = window.state.filtered_df.iloc[0]["cveID"]
    window.show_cve(cve)
    assert window.state.selected_cve == cve
    assert window.details.name.text() != "未选择记录"
    destination = window.export_to_path(tmp_path / "filtered")
    exported = pd.read_csv(destination)
    assert destination.suffix == ".csv"
    assert len(exported) == len(window.state.filtered_df)
    assert exported["cwes"].map(lambda value: isinstance(value, str) or pd.isna(value)).all()
    chart_path = window.export_chart_to_path(tmp_path / "visualization")
    assert chart_path.exists() and chart_path.suffix == ".png"
    window.tabs.setCurrentWidget(window.result_split)
    assert window.export_chart_button.text() == "导出当前表格 PNG"
    table_path = window.export_chart_to_path(tmp_path / "results_and_details")
    assert table_path.exists() and table_path.suffix == ".png"
    window.reset_filters()
    assert len(window.state.filtered_df) == 1656
    window.close()
