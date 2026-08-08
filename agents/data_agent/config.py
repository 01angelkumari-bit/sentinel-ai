from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field, model_validator


class SourceConfig(BaseModel):
    table: str | None = None
    query: str | None = None
    query_parameters: dict[str, Any] = Field(default_factory=dict)
    columns: list[str] = Field(default_factory=list)
    incremental_column: str | None = None
    incremental_value: Any | None = None
    batch_size: int = Field(default=10_000, ge=100, le=250_000)
    max_rows: int = Field(default=1_000_000, ge=1)

    @model_validator(mode="after")
    def exactly_one_source(self) -> "SourceConfig":
        if bool(self.table) == bool(self.query):
            raise ValueError("Configure exactly one of table or query")
        return self


class ColumnSchema(BaseModel):
    type: Literal["string", "integer", "float", "boolean", "date", "datetime", "email", "phone", "currency"] = "string"
    required: bool = False
    nullable: bool = True
    primary_key: bool = False
    minimum: float | None = None
    maximum: float | None = None
    pattern: str | None = None


class MissingValueRule(BaseModel):
    strategy: Literal["mean", "median", "mode", "constant", "forward_fill", "backward_fill", "drop_rows", "drop_column", "custom"]
    value: Any | None = None
    custom_handler: str | None = None


class CleaningRule(BaseModel):
    trim: bool = True
    lowercase: bool = False
    uppercase: bool = False
    titlecase: bool = False
    normalize_unicode: bool = True
    remove_invalid_pattern: str | None = None
    date_format: str = "%Y-%m-%d"


class NormalizationRule(BaseModel):
    method: Literal["min_max", "standard", "z_score", "label", "one_hot"]


class ForeignKeyRule(BaseModel):
    column: str
    reference_query: str
    reference_column: str
    parameters: dict[str, Any] = Field(default_factory=dict)


class DataAgentSettings(BaseModel):
    database_url: str = Field(repr=False)
    source: SourceConfig
    schema_rules: dict[str, ColumnSchema]
    allow_unexpected_columns: bool = True
    missing_values: dict[str, MissingValueRule] = Field(default_factory=dict)
    cleaning: dict[str, CleaningRule] = Field(default_factory=dict)
    normalization: dict[str, NormalizationRule] = Field(default_factory=dict)
    foreign_keys: list[ForeignKeyRule] = Field(default_factory=list)
    output_format: Literal["records", "columns", "json"] = "records"
    log_level: str = "INFO"
    pool_size: int = Field(default=5, ge=1, le=50)
    max_overflow: int = Field(default=10, ge=0, le=100)
    pool_timeout_seconds: int = Field(default=30, ge=1, le=300)
    statement_timeout_seconds: int = Field(default=60, ge=1, le=3600)
    reconnect_attempts: int = Field(default=3, ge=1, le=10)
    downstream_agents: list[str] = Field(default_factory=lambda: ["analytics", "report", "visualization", "ml", "recommendation", "pdf", "dashboard"])

    @classmethod
    def from_yaml(cls, path: str | Path, *, environment: dict[str, str] | None = None) -> "DataAgentSettings":
        env = environment or os.environ
        with Path(path).open("r", encoding="utf-8") as stream:
            payload = yaml.safe_load(stream) or {}
        database_url_env = payload.pop("database_url_env", "DATABASE_URL")
        database_url = env.get(database_url_env)
        if not database_url:
            raise ValueError(f"Required database environment variable {database_url_env!r} is not set")
        return cls(database_url=database_url, **payload)
