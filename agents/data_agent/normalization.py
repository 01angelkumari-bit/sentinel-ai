from __future__ import annotations

import pandas as pd

from .config import DataAgentSettings


class DataNormalizer:
    def __init__(self, settings: DataAgentSettings) -> None:
        self.settings = settings

    def normalize(self, frame: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
        transformations: list[str] = []
        for column, rule in self.settings.normalization.items():
            if column not in frame: continue
            if rule.method in {"min_max", "standard", "z_score"}:
                values = pd.to_numeric(frame[column], errors="coerce")
                if rule.method == "min_max":
                    span = values.max() - values.min()
                    frame[column] = (values - values.min()) / span if span else 0.0
                else:
                    deviation = values.std(ddof=0)
                    frame[column] = (values - values.mean()) / deviation if deviation else 0.0
            elif rule.method == "label":
                categories = sorted(str(value) for value in frame[column].dropna().unique())
                frame[column] = frame[column].astype("string").map({value: index for index, value in enumerate(categories)}).astype("Int64")
            elif rule.method == "one_hot":
                encoded = pd.get_dummies(frame[column], prefix=column, dtype="int8")
                frame = pd.concat([frame.drop(columns=[column]), encoded], axis=1)
            transformations.append(f"applied {rule.method} normalization to {column}")
        return frame, transformations
