"""Safe bridge from Plotly click events to Qt signals."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import unquote

from plotly.io import to_html
from plotly.offline import get_plotlyjs
from PyQt6.QtCore import QObject, QUrl, pyqtSignal
from PyQt6.QtWebEngineWidgets import QWebEngineView


class WebBridge(QObject):
    """Receive a vendor label selected inside a Plotly WebEngine page."""

    vendor_selected = pyqtSignal(str)

    def select_vendor(self, vendor: str) -> None:
        self.vendor_selected.emit(vendor)


def configure_channel(view: QWebEngineView, bridge: WebBridge) -> WebBridge:
    """Forward ``#vendor=...`` page fragments without Qt WebChannel ABI risk."""
    def handle_url(url: QUrl) -> None:
        fragment = url.fragment()
        if fragment.startswith("vendor="):
            bridge.select_vendor(unquote(fragment.removeprefix("vendor=")))

    view.urlChanged.connect(handle_url)
    return bridge


def ensure_plotly_runtime(directory: Path) -> Path:
    """Write the installed Plotly runtime once for fully offline WebEngine pages."""
    directory.mkdir(parents=True, exist_ok=True)
    runtime = directory / "plotly.min.js"
    if not runtime.exists():
        runtime.write_text(get_plotlyjs(), encoding="utf-8")
    return runtime


def write_plotly_page(
    figure,
    directory: Path,
    filename: str,
    *,
    click_customdata: bool = False,
    adaptive_3d_markers: bool = False,
    vertical_scroll: bool = False,
) -> Path:
    """Create an offline Plotly page and optionally forward point customdata."""
    ensure_plotly_runtime(directory)
    fragment = to_html(
        figure,
        full_html=False,
        include_plotlyjs=False,
        config={
            "displaylogo": False,
            "responsive": True,
            "scrollZoom": not vertical_scroll,
            "modeBarButtonsToRemove": ["sendDataToCloud", "resetCameraLastSave3d"],
        },
        div_id="kev-plot",
    )
    bridge_script = ""
    if click_customdata:
        bridge_script = """
<script>
document.getElementById('kev-plot').on('plotly_click', function(event) {
  const point = event.points && event.points[0];
  if (point && point.customdata) {
    window.location.hash = 'vendor=' + encodeURIComponent(String(point.customdata));
  }
});
</script>"""
    zoom_script = ""
    if adaptive_3d_markers:
        zoom_script = """
<script>
(function() {
  const plot = document.getElementById('kev-plot');
  const vendorTraceIndex = 2;
  if (!plot.data[vendorTraceIndex] || !plot.data[vendorTraceIndex].marker) return;
  const originalSizes = Array.from(plot.data[vendorTraceIndex].marker.size);
  plot.on('plotly_relayout', function(event) {
    const camera = event['scene.camera'];
    if (!camera || !camera.eye) return;
    const eye = camera.eye;
    const distance = Math.sqrt(eye.x * eye.x + eye.y * eye.y + eye.z * eye.z);
    const scale = Math.max(0.20, Math.min(1.0, distance / 2.35));
    const sizes = originalSizes.map(function(size) { return Math.max(7, size * scale); });
    Plotly.restyle(plot, {'marker.size': [sizes]}, [vendorTraceIndex]);
  });
})();
</script>"""
    page = directory / filename
    overflow = "auto" if vertical_scroll else "hidden"
    plot_height = "auto" if vertical_scroll else "100%"
    page.write_text(
        "<!doctype html><html><head><meta charset='utf-8'>"
        f"<style>html,body{{width:100%;height:100%;margin:0;background:#f7f9fb;overflow:{overflow}}}"
        f"#kev-plot{{width:100%;height:{plot_height};margin:0;background:#f7f9fb}}</style>"
        "<script src='plotly.min.js'></script></head><body>"
        f"{fragment}{bridge_script}{zoom_script}</body></html>",
        encoding="utf-8",
    )
    return page
