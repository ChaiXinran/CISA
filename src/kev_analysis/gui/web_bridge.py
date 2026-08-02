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
    background: str = "#f7f9fb",
    starfield: bool = False,
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
  const starCanvas = document.getElementById('starfield');
  const starContext = starCanvas ? starCanvas.getContext('2d') : null;
  if (!starCanvas || !starContext) return;

  // Deterministic points on a celestial sphere. They are projected from the
  // current camera on every drag, so rotating the globe reveals another sky.
  let seed = 17391;
  function random() {
    seed = (seed * 1664525 + 1013904223) >>> 0;
    return seed / 4294967296;
  }
  const stars = Array.from({length: 300}, function() {
    const z = random() * 2 - 1;
    const angle = random() * Math.PI * 2;
    const radius = Math.sqrt(1 - z * z);
    return {
      x: radius * Math.cos(angle), y: radius * Math.sin(angle), z: z,
      size: random() > 0.94 ? 1.65 : (0.55 + random() * 0.75),
      alpha: 0.28 + random() * 0.62
    };
  });

  function basisFor(eye) {
    const distance = Math.hypot(eye.x, eye.y, eye.z);
    const forward = {x: -eye.x / distance, y: -eye.y / distance, z: -eye.z / distance};
    let right = {x: forward.y, y: -forward.x, z: 0};
    let rightLength = Math.hypot(right.x, right.y, right.z);
    if (rightLength < 0.001) {
      right = {x: 1, y: 0, z: 0}; rightLength = 1;
    }
    right = {x: right.x / rightLength, y: right.y / rightLength, z: right.z / rightLength};
    const up = {
      x: right.y * forward.z - right.z * forward.y,
      y: right.z * forward.x - right.x * forward.z,
      z: right.x * forward.y - right.y * forward.x
    };
    return {distance: distance, forward: forward, right: right, up: up};
  }
  function dot(a, b) { return a.x * b.x + a.y * b.y + a.z * b.z; }

  let lastCamera = null;
  let framePending = false;
  function render(camera) {
    if (!camera || !camera.eye) return;
    const eye = camera.eye;
    const basis = basisFor(eye);
    const width = plot.clientWidth;
    const height = plot.clientHeight;
    const centerX = width * 0.47;
    const centerY = height * 0.54;
    const ratio = Math.min(window.devicePixelRatio || 1, 1.5);
    const targetWidth = Math.round(width * ratio);
    const targetHeight = Math.round(height * ratio);
    if (starCanvas.width !== targetWidth || starCanvas.height !== targetHeight) {
      starCanvas.width = targetWidth;
      starCanvas.height = targetHeight;
      starCanvas.style.width = width + 'px';
      starCanvas.style.height = height + 'px';
    }
    starContext.setTransform(ratio, 0, 0, ratio, 0, 0);
    starContext.clearRect(0, 0, width, height);
    const focal = Math.min(width, height) * 0.52;
    stars.forEach(function(star) {
      const depth = dot(star, basis.forward);
      if (depth < 0.34) return;
      const screenX = centerX + dot(star, basis.right) / depth * focal;
      const screenY = centerY - dot(star, basis.up) / depth * focal;
      if (screenX < 0 || screenX > width || screenY < 0 || screenY > height) return;
      starContext.beginPath();
      starContext.fillStyle = 'rgba(220,235,255,' + star.alpha + ')';
      starContext.arc(screenX, screenY, star.size, 0, Math.PI * 2);
      starContext.fill();
    });
  }

  function schedule(camera) {
    lastCamera = camera;
    if (framePending) return;
    framePending = true;
    window.requestAnimationFrame(function() {
      framePending = false;
      render(lastCamera);
    });
  }

  plot.on('plotly_relayout', function(event) {
    if (event['scene.camera']) schedule(event['scene.camera']);
  });
  window.addEventListener('resize', function() { schedule(plot.layout.scene.camera); });
  window.setTimeout(function() { schedule(plot.layout.scene.camera); }, 80);
})();
</script>"""
    page = directory / filename
    overflow = "auto" if vertical_scroll else "hidden"
    plot_height = "auto" if vertical_scroll else "100%"
    overlay_markup = "<canvas id='starfield'></canvas>" if starfield else ""
    page.write_text(
        "<!doctype html><html><head><meta charset='utf-8'>"
        f"<style>html,body{{width:100%;height:100%;margin:0;background:{background};overflow:{overflow}}}"
        "#starfield{position:absolute;inset:0;width:100%;height:100%;z-index:0;pointer-events:none;}"
        f"#kev-plot{{position:relative;z-index:1;width:100%;height:{plot_height};margin:0;background:transparent}}</style>"
        "<script src='plotly.min.js'></script></head><body>"
        f"{overlay_markup}{fragment}{bridge_script}{zoom_script}</body></html>",
        encoding="utf-8",
    )
    return page
