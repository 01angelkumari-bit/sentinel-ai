from __future__ import annotations

import re
from typing import Any

import pandas as pd

from .config import ColumnSchema, DataAgentSettings
from .models import QualityIssue, SchemaInformation, ValidationSummary
from .postgres import PostgreSQLConnector


TYPE_COERCERS = {
    "string": lambda series: series.astype("string"),
    "email": lambda series: series.astype("string"),
    "phone": lambda series: series.astype("string"),
    "currency": lambda series: pd.to_numeric(series.astype("string").str.replace(r"[^0-9.\-]", "", regex=True), errors="coerce"),
    "integer": lambda series: pd.to_numeric(series, errors="coerce").astype("Int64"),
    "float": lambda series: pd.to_numeric(series, errors="coerce"),
    "boolean": lambda series: series.map({True: True, False: False, 1: True, 0: False, "true": True, "false": False, "yes": True, "no": False}).astype("boolean"),
    "date": lambda series: pd.to_datetime(series, errors="coerce").dt.date,
    "datetime": lambda series: pd.to_datetime(series, errors="coerce", utc=True),
}


class DataValidator:
    def __init__(self, settings: DataAgentSettings, connector: PostgreSQLConnector) -> None:
        self.settings = settings
        self.connector = connector

    def validate(self, frame: pd.DataFrame) -> tuple[pd.DataFrame, ValidationSummary, SchemaInformation, list[QualityIssue]]:
        rules = self.settings.schema_rules
        required = [column for column, rule in rules.items() if rule.required]
        missing = sorted(set(required) - set(frame.columns))
        unexpected = sorted(set(frame.columns) - set(rules))
        issues: list[QualityIssue] = []
        for column in missing:
            issues.append(QualityIssue(severity="error", code="missing_column", column=column, message=f"Required column {column!r} is missing"))
        if unexpected and not self.settings.allow_unexpected_columns:
            issues.append(QualityIssue(severity="error", code="unexpected_columns", message=f"Unexpected columns: {', '.join(unexpected)}"))

        coerced: list[str] = []
        for column, rule in rules.items():
            if column not in frame:
                continue
            before_nulls = int(frame[column].isna().sum())
            try:
                frame[column] = TYPE_COERCERS[rule.type](frame[column])
                coerced.append(column)
            except (TypeError, ValueError) as exc:
                issues.append(QualityIssue(severity="error", code="type_coercion", column=column, message=f"Could not coerce {column!r} to {rule.type}: {exc}"))
                continue
            new_invalid = max(0, int(frame[column].isna().sum()) - before_nulls)
            if new_invalid:
                issues.append(QualityIssue(severity="error", code="invalid_type", column=column, message=f"{new_invalid} values could not be parsed as {rule.type}", affected_rows=new_invalid))
            issues.extend(self._column_checks(frame[column], column, rule))

        primary_keys = [column for column, rule in rules.items() if rule.primary_key]
        primary_key_valid = True
        for column in primary_keys:
            if column in frame:
                invalid = int(frame[column].isna().sum() + frame[column].duplicated(keep=False).sum())
                if invalid:
                    primary_key_valid = False
                    issues.append(QualityIssue(severity="error", code="invalid_primary_key", column=column, message="Primary key contains null or duplicate values", affected_rows=invalid))
        foreign_keys_valid = self._foreign_key_checks(frame, issues)
        summary = ValidationSummary(valid=not any(issue.severity == "error" for issue in issues), required_columns=required, missing_columns=missing, unexpected_columns=unexpected, coerced_columns=coerced, primary_key_valid=primary_key_valid, foreign_keys_valid=foreign_keys_valid)
        schema = SchemaInformation(columns={column: str(dtype) for column, dtype in frame.dtypes.items()}, nullable_counts={column: int(frame[column].isna().sum()) for column in frame.columns}, primary_keys=primary_keys)
        return frame, summary, schema, issues

    @staticmethod
    def _column_checks(series: pd.Series, column: str, rule: ColumnSchema) -> list[QualityIssue]:
        issues: list[QualityIssue] = []
        if not rule.nullable:
            count = int(series.isna().sum())
            if count:
                issues.append(QualityIssue(severity="error", code="null_not_allowed", column=column, message="Null values are not allowed", affected_rows=count))
        numeric = pd.to_numeric(series, errors="coerce") if rule.minimum is not None or rule.maximum is not None else None
        if numeric is not None:
            invalid = pd.Series(False, index=series.index)
            if rule.minimum is not None: invalid |= numeric < rule.minimum
            if rule.maximum is not None: invalid |= numeric > rule.maximum
            count = int(invalid.sum())
            if count: issues.append(QualityIssue(severity="error", code="out_of_range", column=column, message="Values fall outside the configured range", affected_rows=count, sample_values=series[invalid].head(5).tolist()))
        if rule.pattern:
            valid = series.isna() | series.astype("string").str.fullmatch(re.compile(rule.pattern), na=False)
            count = int((~valid).sum())
            if count: issues.append(QualityIssue(severity="error", code="invalid_format", column=column, message="Values do not match the configured pattern", affected_rows=count, sample_values=series[~valid].head(5).tolist()))
        return issues

    def _foreign_key_checks(self, frame: pd.DataFrame, issues: list[QualityIssue]) -> bool:
        valid = True
        for rule in self.settings.foreign_keys:
            if rule.column not in frame: continue
            reference = self.connector.execute_frame(rule.reference_query, rule.parameters)
            if rule.reference_column not in reference:
                issues.append(QualityIssue(severity="error", code="foreign_key_reference_missing", column=rule.column, message=f"Reference query did not return {rule.reference_column!r}")); valid = False; continue
            invalid = ~frame[rule.column].isna() & ~frame[rule.column].isin(set(reference[rule.reference_column].dropna()))
            count = int(invalid.sum())
            if count:
                valid = False
                issues.append(QualityIssue(severity="error", code="invalid_foreign_key", column=rule.column, message="Values do not exist in the reference dataset", affected_rows=count, sample_values=frame.loc[invalid, rule.column].head(5).tolist()))
        return valid
