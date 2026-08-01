"""Offline 3D globe showing KEV vendor labels by documented headquarters."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from PIL import Image
from PyQt6.QtCore import QUrl, pyqtSignal
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget
from PyQt6.QtWebEngineWidgets import QWebEngineView

from .chart_export import export_widget_png
from .web_bridge import WebBridge, configure_channel, write_plotly_page

LOCATION_COLUMNS = [
    "vendor_clean", "country", "city", "latitude", "longitude", "location_type", "source"
]

GLOBE_LONGITUDE_SAMPLES = 721
GLOBE_LATITUDE_SAMPLES = 361


def default_location_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "vendor_locations.csv"


def default_boundary_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "ne_110m_admin_0_countries.geojson"


def default_texture_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "nasa_blue_marble_2048.jpg"


@lru_cache(maxsize=2)
def load_earth_texture(
    path: str | Path | None = None,
    width: int = GLOBE_LONGITUDE_SAMPLES,
    height: int = GLOBE_LATITUDE_SAMPLES,
    colors: int = 256,
) -> tuple[np.ndarray, list[list[object]]]:
    """Load NASA Blue Marble as a Plotly-compatible indexed surface texture."""
    source = Path(path) if path is not None else default_texture_path()
    with Image.open(source) as image:
        resized = image.convert("RGB").resize((width, height), Image.Resampling.LANCZOS)
        indexed = resized.quantize(colors=colors, method=Image.Quantize.MEDIANCUT)
        indices = np.flipud(np.asarray(indexed, dtype=float))
        palette = indexed.getpalette()[: colors * 3]
    colorscale = []
    for index in range(colors):
        red, green, blue = palette[index * 3:index * 3 + 3]
        colorscale.append([index / (colors - 1), f"rgb({red},{green},{blue})"])
    return indices, colorscale


@lru_cache(maxsize=2)
def load_boundary_lines(path: str | Path | None = None) -> tuple[list[float | None], ...]:
    """Convert local Natural Earth polygon rings to one offline 3D line layer."""
    source = Path(path) if path is not None else default_boundary_path()
    payload = json.loads(source.read_text(encoding="utf-8"))
    line_x: list[float | None] = []
    line_y: list[float | None] = []
    line_z: list[float | None] = []
    radius = 1.003
    for feature in payload.get("features", []):
        geometry = feature.get("geometry") or {}
        coordinates = geometry.get("coordinates", [])
        if geometry.get("type") == "Polygon":
            polygons = [coordinates]
        elif geometry.get("type") == "MultiPolygon":
            polygons = coordinates
        else:
            continue
        for polygon in polygons:
            for ring in polygon:
                if not ring:
                    continue
                longitude = np.radians([point[0] for point in ring])
                latitude = np.radians([point[1] for point in ring])
                line_x.extend((radius * np.cos(latitude) * np.cos(longitude)).tolist())
                line_y.extend((radius * np.cos(latitude) * np.sin(longitude)).tolist())
                line_z.extend((radius * np.sin(latitude)).tolist())
                line_x.append(None); line_y.append(None); line_z.append(None)
    return line_x, line_y, line_z


def load_vendor_locations(path: str | Path | None = None) -> pd.DataFrame:
    """Load and validate the documented vendor headquarters mapping."""
    source = Path(path) if path is not None else default_location_path()
    locations = pd.read_csv(source)
    missing = [column for column in LOCATION_COLUMNS if column not in locations.columns]
    if missing:
        raise ValueError(f"厂商位置表缺少字段：{missing}")
    if locations["vendor_clean"].duplicated().any():
        raise ValueError("厂商位置表中的 vendor_clean 必须唯一")
    coordinates = locations[["latitude", "longitude"]].notna().all(axis=1)
    if not locations.loc[coordinates, "latitude"].between(-90, 90).all():
        raise ValueError("latitude 必须位于 [-90, 90]")
    if not locations.loc[coordinates, "longitude"].between(-180, 180).all():
        raise ValueError("longitude 必须位于 [-180, 180]")
    return locations[LOCATION_COLUMNS].copy()


def aggregate_vendor_locations(
    filtered_df: pd.DataFrame,
    locations: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Aggregate current records by vendor and join only documented locations."""
    required = {"vendor_clean", "knownRansomwareCampaignUse"}
    missing = sorted(required.difference(filtered_df.columns))
    if missing:
        raise KeyError(f"filtered_df 缺少字段：{missing}")
    rows = []
    for vendor, group in filtered_df.groupby("vendor_clean", sort=False):
        count = len(group)
        known = int(group["knownRansomwareCampaignUse"].eq("Known").sum())
        rows.append({
            "vendor_clean": vendor,
            "count": count,
            "known_count": known,
            "known_share": known / count if count else 0.0,
        })
    counts = pd.DataFrame(rows, columns=["vendor_clean", "count", "known_count", "known_share"])
    joined = counts.merge(locations, on="vendor_clean", how="left", validate="one_to_one")
    mapped_mask = joined[["latitude", "longitude"]].notna().all(axis=1)
    mapped = joined.loc[mapped_mask].copy()
    summary = {
        "mapped_records": int(mapped["count"].sum()) if not mapped.empty else 0,
        "unmapped_records": int(joined.loc[~mapped_mask, "count"].sum()) if not joined.empty else 0,
        "mapped_vendors": int(mapped_mask.sum()),
        "unmapped_vendors": int((~mapped_mask).sum()),
    }
    return mapped, summary


def build_globe_figure(mapped: pd.DataFrame) -> go.Figure:
    """Build a fully offline 3D globe; locations represent headquarters only."""
    # Half-degree sampling keeps the NASA texture clear while reducing the
    # surface to about 260k vertices for smoother WebEngine interaction.
    longitude = np.linspace(-np.pi, np.pi, GLOBE_LONGITUDE_SAMPLES)
    latitude = np.linspace(-np.pi / 2, np.pi / 2, GLOBE_LATITUDE_SAMPLES)
    lon_grid, lat_grid = np.meshgrid(longitude, latitude)
    sphere_x = np.cos(lat_grid) * np.cos(lon_grid)
    sphere_y = np.cos(lat_grid) * np.sin(lon_grid)
    sphere_z = np.sin(lat_grid)
    texture, texture_colorscale = load_earth_texture(width=len(longitude), height=len(latitude))
    figure = go.Figure(go.Surface(
        x=sphere_x, y=sphere_y, z=sphere_z,
        surfacecolor=texture,
        colorscale=texture_colorscale, cmin=0, cmax=len(texture_colorscale) - 1,
        showscale=False, hoverinfo="skip", opacity=1.0,
        # Uniform ambient illumination preserves the NASA texture without a
        # moving white WebGL glare spot on the globe.
        lighting={
            "ambient": 1.0, "diffuse": 0.0, "roughness": 1.0,
            "specular": 0.0, "fresnel": 0.0,
        },
    ))
    boundary_x, boundary_y, boundary_z = load_boundary_lines()
    figure.add_trace(go.Scatter3d(
        x=boundary_x, y=boundary_y, z=boundary_z,
        mode="lines", hoverinfo="skip", showlegend=False,
        line={"color": "#d9e8d2", "width": 1.4},
        name="Natural Earth 国家边界",
    ))
    if not mapped.empty:
        lat_radians = np.radians(mapped["latitude"].astype(float).to_numpy())
        lon_radians = np.radians(mapped["longitude"].astype(float).to_numpy())
        radius = 1.018
        point_x = radius * np.cos(lat_radians) * np.cos(lon_radians)
        point_y = radius * np.cos(lat_radians) * np.sin(lon_radians)
        point_z = radius * np.sin(lat_radians)
        sizes = 19 + 31 * (mapped["count"] / mapped["count"].max()) ** 0.5
        labels = mapped["vendor_clean"].astype(str).tolist()
        hover = (
            "<b>" + mapped["vendor_clean"].astype(str) + "</b><br>"
            + mapped["city"].astype(str) + ", " + mapped["country"].astype(str)
            + "<br>当前 KEV 记录：" + mapped["count"].astype(str)
            + "<br>Known 占比：" + mapped["known_share"].map(lambda value: f"{value:.1%}")
            + "<br>位置口径：厂商总部<extra></extra>"
        )
        figure.add_trace(go.Scatter3d(
            x=point_x, y=point_y, z=point_z, hovertext=hover,
            customdata=mapped["vendor_clean"], hovertemplate="%{hovertext}",
            mode="markers+text", text=labels, textposition="top center",
            textfont={"size": 11, "color": "#071b2b", "family": "Arial Black"},
            marker={
                "size": sizes, "color": mapped["known_share"], "colorscale": "YlOrRd",
                "cmin": 0, "cmax": 1, "opacity": 1.0,
                "line": {"color": "#061520", "width": 2.2},
                "colorbar": {
                    "title": {"text": "Known", "side": "right"},
                    "tickformat": ".0%", "x": 1.01, "y": 0.46, "len": 0.52,
                    "thickness": 13, "outlinewidth": 0,
                },
            },
            name="厂商总部位置", showlegend=False,
        ))
    figure.update_layout(
        margin={"l": 8, "r": 92, "t": 76, "b": 8},
        paper_bgcolor="#f7f9fb", height=560,
        title={
            "text": "按厂商总部所在地映射的 KEV 厂商标签记录",
            "x": 0.02, "xanchor": "left", "y": 0.97, "yanchor": "top",
            "font": {"size": 17},
        },
        scene={
            "aspectmode": "cube",
            "xaxis": {"visible": False, "range": [-1.15, 1.15]},
            "yaxis": {"visible": False, "range": [-1.15, 1.15]},
            "zaxis": {"visible": False, "range": [-1.15, 1.15]},
            "camera": {"eye": {"x": 1.65, "y": 1.45, "z": 0.85}},
            "bgcolor": "#f7f9fb",
        },
        dragmode="orbit",
    )
    return figure


class GlobeView(QWidget):
    """WebEngine globe implementing the shared update/export contract."""

    vendor_selected = pyqtSignal(str)

    def __init__(self, location_path: str | Path | None = None, parent=None) -> None:
        super().__init__(parent)
        self._data = pd.DataFrame()
        self.locations = load_vendor_locations(location_path)
        self._temporary = TemporaryDirectory(prefix="kev_globe_")
        self._web_directory = Path(self._temporary.name)
        self.summary = QLabel("尚未加载数据")
        self.summary.setWordWrap(True)
        self.web = QWebEngineView()
        self.bridge = WebBridge(self)
        self._channel = configure_channel(self.web, self.bridge)
        self.bridge.vendor_selected.connect(self.vendor_selected)
        layout = QVBoxLayout(self)
        layout.addWidget(self.summary)
        layout.addWidget(self.web, 1)

    def update_data(self, filtered_df: pd.DataFrame) -> None:
        self._data = filtered_df.copy(deep=True)
        mapped, counts = aggregate_vendor_locations(self._data, self.locations)
        self.summary.setText(
            f"已映射 {counts['mapped_records']:,} 条/{counts['mapped_vendors']:,} 个厂商；"
            f"未映射 {counts['unmapped_records']:,} 条/{counts['unmapped_vendors']:,} 个厂商。"
            "位置仅表示厂商总部，不表示漏洞、攻击、设备或受害者所在地。"
        )
        page = write_plotly_page(
            build_globe_figure(mapped), self._web_directory, "globe.html", click_customdata=True
        )
        self.web.setUrl(QUrl.fromLocalFile(str(page)))

    def export_png(self, path: str | Path) -> None:
        export_widget_png(self, path)
