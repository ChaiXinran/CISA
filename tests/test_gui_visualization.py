import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--no-sandbox --disable-gpu")

import numpy as np
import pandas as pd
from kev_analysis.gui.chart_export import normalized_png_path
from kev_analysis.gui.chart_panel import VisualizationPanel, build_linked_figures
from kev_analysis.gui.globe_view import (
    aggregate_vendor_locations, build_globe_figure, load_boundary_lines,
    load_earth_texture, load_political_texture, load_vendor_locations,
)
from kev_analysis.gui.three_globe import write_three_globe_page
from kev_analysis.analysis.cwe import build_cwe_summary, explode_cwes
from kev_analysis.analysis.vendor import build_vendor_summary


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
    assert len(figures["vendor"].data[0].y) == len(build_vendor_summary(prepared_df))
    assert len(figures["cwe"].data[0].y) == len(
        build_cwe_summary(explode_cwes(prepared_df), len(prepared_df))
    )
    empty = prepared_df.iloc[0:0].copy()
    assert set(build_linked_figures(empty)) == {"monthly", "vendor", "cwe"}


def test_globe_is_fully_local_3d_surface():
    locations = load_vendor_locations().head(2).copy()
    locations["count"] = [10, 5]
    locations["known_count"] = [4, 1]
    locations["known_share"] = [0.4, 0.2]
    figure = build_globe_figure(locations)
    assert figure.data[0].type == "surface"
    assert figure.data[0].opacity == 1.0
    assert figure.data[0].lighting.specular == 0.03
    assert figure.data[0].lighting.diffuse == 0.62
    assert figure.layout.paper_bgcolor == "rgba(0,0,0,0)"
    assert figure.data[1].type == "scatter3d"
    assert figure.data[1].mode == "lines"
    assert figure.data[2].type == "scatter3d"
    assert figure.data[2].mode == "markers+text"
    assert list(figure.data[2].text) == ["Microsoft", "Cisco"]
    assert list(figure.data[2].meta) == [10, 5]
    assert max(figure.data[2].marker.size) <= 26
    assert figure.data[2].name == "厂商总部位置"
    assert figure.layout.geo.to_plotly_json() == {}


def test_natural_earth_boundaries_are_local_3d_lines():
    x, y, z = load_boundary_lines()
    assert len(x) == len(y) == len(z)
    assert len(x) > 5_000
    assert any(value is None for value in x)


def test_nasa_texture_is_local_and_matches_surface_grid():
    texture, colorscale = load_earth_texture()
    assert texture.shape == (361, 721)
    assert len(colorscale) == 256
    assert float(texture.min()) >= 0
    assert float(texture.max()) <= 255


def test_political_texture_is_local_and_terrain_free():
    texture, colorscale = load_political_texture()
    assert texture.shape == (361, 721)
    assert len(colorscale) == 7
    assert set(np.unique(texture)).issubset(set(range(7)))


def test_three_globe_page_is_fully_local_and_contains_vendor_data(tmp_path):
    locations = load_vendor_locations().head(2).copy()
    locations["count"] = [10, 5]
    locations["known_count"] = [4, 1]
    locations["known_share"] = [0.4, 0.2]
    page = write_three_globe_page(locations, tmp_path)
    html = page.read_text(encoding="utf-8")
    assert (tmp_path / "three.min.js").exists()
    assert (tmp_path / "earth-political.png").exists()
    assert '<script src="three.min.js"></script>' in html
    assert "new THREE.Points" in html
    assert "vendor-label" in html
    assert 'id="tooltip"' in html
    assert "distance=3.65" in html
    assert "theta+=(e.clientX-lastX)*.006" in html
    assert "phi-(e.clientY-lastY)*.006" in html
    assert "v.vendor+'\\n'" in html
    assert "Microsoft" in html and "Cisco" in html


def test_visualization_panel_exposes_fixed_contract():
    assert callable(VisualizationPanel.update_data)
    assert callable(VisualizationPanel.export_png)


def test_png_extension_is_normalized(tmp_path):
    assert normalized_png_path(tmp_path / "chart").suffix == ".png"
    assert normalized_png_path(tmp_path / "chart.PNG").name == "chart.PNG"
