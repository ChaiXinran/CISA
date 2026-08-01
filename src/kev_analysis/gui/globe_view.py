"""Offline 3D globe showing KEV vendor labels by documented headquarters."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd
import plotly.graph_objects as go
from PyQt6.QtCore import QUrl, pyqtSignal
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget
from PyQt6.QtWebEngineWidgets import QWebEngineView

from .chart_export import export_widget_png
from .web_bridge import WebBridge, configure_channel, write_plotly_page

LOCATION_COLUMNS = [
    "vendor_clean", "country", "city", "latitude", "longitude", "location_type", "source"
]


def default_location_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "vendor_locations.csv"


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
    """Build an orthographic globe; locations represent headquarters only."""
    figure = go.Figure()
    if not mapped.empty:
        sizes = 8 + 34 * (mapped["count"] / mapped["count"].max()) ** 0.5
        hover = (
            "<b>" + mapped["vendor_clean"].astype(str) + "</b><br>"
            + mapped["city"].astype(str) + ", " + mapped["country"].astype(str)
            + "<br>当前 KEV 记录：" + mapped["count"].astype(str)
            + "<br>Known 占比：" + mapped["known_share"].map(lambda value: f"{value:.1%}")
            + "<br>位置口径：厂商总部<extra></extra>"
        )
        figure.add_trace(go.Scattergeo(
            lat=mapped["latitude"], lon=mapped["longitude"], text=hover,
            customdata=mapped["vendor_clean"], hovertemplate="%{text}",
            mode="markers", marker={
                "size": sizes, "color": mapped["known_share"], "colorscale": "YlOrRd",
                "cmin": 0, "cmax": 1, "opacity": 0.88,
                "line": {"color": "#ffffff", "width": 1},
                "colorbar": {"title": "Known 占比", "tickformat": ".0%"},
            },
        ))
    figure.update_geos(
        projection_type="orthographic", showland=True, landcolor="#dce8e5",
        showocean=True, oceancolor="#c9e6f0", showcountries=True, countrycolor="#ffffff",
    )
    figure.update_layout(
        title="按厂商总部所在地映射的 KEV 厂商标签记录",
        margin={"l": 0, "r": 0, "t": 48, "b": 0},
        paper_bgcolor="#f7f9fb", height=560,
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
