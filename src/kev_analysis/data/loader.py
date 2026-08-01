"""Load the frozen CISA KEV JSON without flattening multi-value CWEs."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd


def compute_sha256(path: str | Path) -> str:
    """Return the uppercase SHA-256 digest of *path*."""

    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def load_catalog(path: str | Path) -> tuple[dict[str, Any], pd.DataFrame]:
    """Read catalog metadata and vulnerabilities from a KEV JSON file.

    The returned metadata excludes the potentially large ``vulnerabilities``
    array. The ``cwes`` column is retained as Python lists.
    """

    source_path = Path(path)
    with source_path.open("r", encoding="utf-8") as source:
        payload = json.load(source)

    if not isinstance(payload, dict):
        raise ValueError("The KEV JSON top level must be an object.")
    vulnerabilities = payload.get("vulnerabilities")
    if not isinstance(vulnerabilities, list):
        raise ValueError("Top-level 'vulnerabilities' must be a list.")

    metadata = {key: value for key, value in payload.items() if key != "vulnerabilities"}
    metadata["actualRecordCount"] = len(vulnerabilities)
    metadata["sourcePath"] = str(source_path)
    metadata["sha256"] = compute_sha256(source_path)
    return metadata, pd.DataFrame(vulnerabilities)

