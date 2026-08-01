import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--no-sandbox --disable-gpu")

import pandas as pd
from kev_analysis.gui.chart_export import normalized_png_path
from kev_analysis.gui.chart_panel import VisualizationPanel, build_linked_figures
from kev_analysis.gui.globe_view import aggregate_vendor_locations, load_vendor_locations


def test_location_table_has_sources_and_valid_coordinates():
    locations = load_vendor_locations()
    assert locations["source"].str.startswith("https://").all()
    assert locations["latitude"].between(-90, 90).all()
    assert locations["longitude"].between(-180, 180).all()
    assert locations["vendor_clean"].is_unique


def test_mapping_counts_mapped_and_unmapped_without_mutation(prepared_df):
    before = prepared_df.copy(deep=True)
    locations = pd.DataFrame([{
        "vendor_clean": "Acme", "country": "Testland", "city": "Test City",
        "latitude": 10.0, "longitude": 20.0, "location_type": "test_headquarters",
        "source": "https://example.test/acme",
    }])
    mapped, summary = aggregate_vendor_locations(prepared_df, locations)
    assert set(mapped["vendor_clean"]) == {"Acme"}
    assert summary["mapped_records"] == 1
    assert summary["unmapped_records"] == 3
    assert summary["mapped_records"] + summary["unmapped_records"] == len(prepared_df)
    pd.testing.assert_frame_equal(prepared_df, before)


def test_linked_figures_handle_data_and_empty_results(prepared_df):
    figures = build_linked_figures(prepared_df)
    assert set(figures) == {"monthly", "vendor", "cwe"}
    empty = prepared_df.iloc[0:0].copy()
    assert set(build_linked_figures(empty)) == {"monthly", "vendor", "cwe"}


def test_visualization_panel_exposes_fixed_contract():
    assert callable(VisualizationPanel.update_data)
    assert callable(VisualizationPanel.export_png)


def test_png_extension_is_normalized(tmp_path):
    assert normalized_png_path(tmp_path / "chart").suffix == ".png"
    assert normalized_png_path(tmp_path / "chart.PNG").name == "chart.PNG"
