from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, TypedDict

from pydantic import BaseModel, Field


class QualityIssue(BaseModel):
    severity: Literal["warning", "error"]
    code: str
    column: str | None = None
    message: str
    affected_rows: int = 0
    sample_values: list[Any] = Field(default_factory=list)


class ValidationSummary(BaseModel):
    valid: bool
    required_columns: list[str]
    missing_columns: list[str] = Field(default_factory=list)
    unexpected_columns: list[str] = Field(default_factory=list)
    coerced_columns: list[str] = Field(default_factory=list)
    primary_key_valid: bool = True
    foreign_keys_valid: bool = True


class SchemaInformation(BaseModel):
    columns: dict[str, str]
    nullable_counts: dict[str, int]
    primary_keys: list[str]


class QualityReport(BaseModel):
    score: float = Field(ge=0, le=100)
    missing_cells: int = 0
    duplicate_rows: int = 0
    invalid_cells: int = 0
    issues: list[QualityIssue] = Field(default_factory=list)


class ExecutionMetadata(BaseModel):
    request_id: str
    organization_id: str
    source: str
    started_at: datetime
    completed_at: datetime
    batches_processed: int
    rows_read: int
    rows_dropped: int
    transformations: list[str] = Field(default_factory=list)
    downstream_agents: list[str] = Field(default_factory=list)


class DataAgentOutput(BaseModel):
    success: bool
    cleaned_data: list[dict[str, Any]] | dict[str, list[Any]] | str
    validation_summary: ValidationSummary
    quality_report: QualityReport
    schema_information: SchemaInformation
    metadata: ExecutionMetadata
    execution_time_seconds: float
    row_count: int
    column_count: int
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class DataAgentState(TypedDict, total=False):
    organization_id: str
    request_id: str
    config_path: str
    query_parameters: dict[str, Any]
    data_agent_output: dict[str, Any]
    cleaned_data: list[dict[str, Any]] | dict[str, list[Any]] | str
    quality_report: dict[str, Any]
    validation_summary: dict[str, Any]
    next_agents: list[str]
    distribution: dict[str, dict[str, Any]]
    warnings: list[str]
    errors: list[str]
