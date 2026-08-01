"""Result objects shared by the data and reporting layers."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class ValidationResult:
    """Machine-readable result of validating a KEV catalog."""

    passed: bool
    checks: dict[str, bool] = field(default_factory=dict)
    statistics: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AnalysisArtifacts:
    """Stable boundary between analysis, export and report layers."""

    tables: dict[str, Any] = field(default_factory=dict)
    metrics: dict[str, Any] = field(default_factory=dict)
    figures: dict[str, Any] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)
