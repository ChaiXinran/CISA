"""PNG export helpers shared by GUI visualization widgets."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtWidgets import QWidget


def normalized_png_path(path: str | Path) -> Path:
    destination = Path(path)
    return destination if destination.suffix.lower() == ".png" else destination.with_suffix(".png")


def export_widget_png(widget: QWidget, path: str | Path) -> Path:
    """Capture the visible widget at device resolution and save it as PNG."""
    destination = normalized_png_path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    pixmap = widget.grab()
    if pixmap.isNull() or not pixmap.save(str(destination), "PNG"):
        raise OSError(f"无法导出 PNG：{destination}")
    return destination
