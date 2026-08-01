"""Qt WebChannel bridge for Plotly click events."""

from __future__ import annotations

import json
from pathlib import Path

from plotly.io import to_html
from plotly.offline import get_plotlyjs
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtWebEngineWidgets import QWebEngineView


class WebBridge(QObject):
    """Receive a vendor label selected inside a Plotly WebEngine page."""

    vendor_selected = pyqtSignal(str)

    @pyqtSlot(str)
    def selectVendor(self, vendor: str) -> None:  # noqa: N802 - JavaScript API
        self.vendor_selected.emit(vendor)


def configure_channel(view: QWebEngineView, bridge: WebBridge) -> QWebChannel:
    """Attach *bridge* to *view* and keep the channel owned by the page."""
    channel = QWebChannel(view.page())
    channel.registerObject("kevBridge", bridge)
    view.page().setWebChannel(channel)
    return channel


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
) -> Path:
    """Create an offline Plotly page and optionally forward point customdata."""
    ensure_plotly_runtime(directory)
    fragment = to_html(
        figure,
        full_html=False,
        include_plotlyjs=False,
        config={"displaylogo": False, "responsive": True},
        div_id="kev-plot",
    )
    bridge_script = ""
    if click_customdata:
        bridge_script = """
<script src="qrc:///qtwebchannel/qwebchannel.js"></script>
<script>
new QWebChannel(qt.webChannelTransport, function(channel) {
  const plot = document.getElementById('kev-plot');
  plot.on('plotly_click', function(event) {
    const point = event.points && event.points[0];
    if (point && point.customdata) {
      channel.objects.kevBridge.selectVendor(String(point.customdata));
    }
  });
});
</script>"""
    page = directory / filename
    page.write_text(
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<style>html,body,#kev-plot{width:100%;height:100%;margin:0;background:#f7f9fb}</style>"
        "<script src='plotly.min.js'></script></head><body>"
        f"{fragment}{bridge_script}</body></html>",
        encoding="utf-8",
    )
    return page
