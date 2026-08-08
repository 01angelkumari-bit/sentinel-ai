from __future__ import annotations

import re
import unicodedata
from collections.abc import Callable
from typing import Any

import pandas as pd

from .config import DataAgentSettings

CustomHandler = Callable[[pd.Series, Any], pd.Series]


class DataCleaner:
    def __init__(self, settings: DataAgentSettings, custom_handlers: dict[str, CustomHandler] | None = None) -> None:
        self.settings = settings
        self.custom_handlers = custom_handlers or {}

    def clean(self, frame: pd.DataFrame) -> tuple[pd.DataFrame, list[str], int, int]:
        transformations: list[str] = []
        original_rows = len(frame)
        duplicate_count = int(frame.duplicated().sum())
        if duplicate_count:
            frame = frame.drop_duplicates().copy()
            transformations.append(f"removed {duplicate_count} duplicate rows")
        for column, rule in self.settings.cleaning.items():
            if column not in frame: continue
            series = frame[column]
            if pd.api.types.is_string_dtype(series.dtype) or series.dtype == object:
                series = series.astype("string")
                if rule.trim: series = series.str.strip()
                if rule.normalize_unicode: series = series.map(lambda value: unicodedata.normalize("NFKC", value) if isinstance(value, str) else value)
                if rule.remove_invalid_pattern: series = series.str.replace(rule.remove_invalid_pattern, "", regex=True)
                if rule.lowercase: series = series.str.lower()
                elif rule.uppercase: series = series.str.upper()
                elif rule.titlecase: series = series.str.title()
                frame[column] = series
                transformations.append(f"normalized text in {column}")
        for column, schema_rule in self.settings.schema_rules.items():
            if column not in frame: continue
            if schema_rule.type == "email": frame[column] = frame[column].astype("string").str.strip().str.lower()
            elif schema_rule.type == "phone": frame[column] = frame[column].astype("string").map(self._phone)
            elif schema_rule.type in {"date", "datetime"}: frame[column] = pd.to_datetime(frame[column], errors="coerce", utc=schema_rule.type == "datetime")
            elif schema_rule.type == "currency": frame[column] = pd.to_numeric(frame[column].astype("string").str.replace(r"[^0-9.\-]", "", regex=True), errors="coerce")
        for column, rule in self.settings.missing_values.items():
            if column not in frame: continue
            before = int(frame[column].isna().sum())
            if not before: continue
            strategy = rule.strategy
            if strategy == "drop_rows": frame = frame.dropna(subset=[column])
            elif strategy == "drop_column": frame = frame.drop(columns=[column])
            elif strategy == "forward_fill": frame[column] = frame[column].ffill()
            elif strategy == "backward_fill": frame[column] = frame[column].bfill()
            elif strategy == "constant": frame[column] = frame[column].fillna(rule.value)
            elif strategy in {"mean", "median"}: frame[column] = frame[column].fillna(getattr(pd.to_numeric(frame[column], errors="coerce"), strategy)())
            elif strategy == "mode":
                mode = frame[column].mode(dropna=True)
                if not mode.empty: frame[column] = frame[column].fillna(mode.iloc[0])
            elif strategy == "custom":
                handler = self.custom_handlers.get(rule.custom_handler or "")
                if not handler: raise ValueError(f"Custom missing-value handler {rule.custom_handler!r} is not registered")
                frame[column] = handler(frame[column], rule.value)
            transformations.append(f"applied {strategy} missing-value strategy to {column} ({before} nulls)")
        return frame.reset_index(drop=True), transformations, original_rows - len(frame), duplicate_count

    @staticmethod
    def _phone(value: Any) -> Any:
        if pd.isna(value): return pd.NA
        digits = re.sub(r"\D", "", str(value))
        if len(digits) == 10: return f"+1{digits}"
        if 11 <= len(digits) <= 15: return f"+{digits}"
        return pd.NA
