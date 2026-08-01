"""Single source of truth shared by GUI components."""

from dataclasses import dataclass, field
from typing import Any

import pandas as pd


@dataclass
class GuiState:
    metadata: dict[str, Any] = field(default_factory=dict)
    raw_df: pd.DataFrame = field(default_factory=pd.DataFrame)
    prepared_df: pd.DataFrame = field(default_factory=pd.DataFrame)
    filtered_df: pd.DataFrame = field(default_factory=pd.DataFrame)
    active_filters: dict[str, Any] = field(default_factory=dict)
    selected_cve: str | None = None

    @property
    def loaded(self) -> bool:
        return not self.prepared_df.empty
