import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PyQt6.QtWidgets import QApplication
from kev_analysis.gui.main_window import MainWindow


@pytest.fixture(scope="module")
def application():
    return QApplication.instance() or QApplication([])


def test_gui_load_filter_reset_and_details(application):
    root = Path(__file__).resolve().parents[1]
    window = MainWindow()
    window.load_path(root / "data/CISA_KEV_2026-07-29.json")
    assert window.state.loaded and len(window.state.filtered_df) == 1656
    assert window.catalog_version.text() == "2026.07.29"
    window.apply_filters({
        "start_date": None, "end_date": None, "vendor": "Microsoft",
        "product": None, "ransomware": "Known", "cwe": None,
    })
    assert not window.state.filtered_df.empty
    assert window.state.filtered_df["vendor_clean"].str.contains("Microsoft", case=False).all()
    assert window.state.filtered_df["knownRansomwareCampaignUse"].eq("Known").all()
    cve = window.state.filtered_df.iloc[0]["cveID"]
    window.show_cve(cve)
    assert window.state.selected_cve == cve
    assert window.details.name.text() != "未选择记录"
    window.reset_filters()
    assert len(window.state.filtered_df) == 1656
    window.close()
