from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import pandas as pd

from .cleaning import CustomHandler, DataCleaner
from .config import DataAgentSettings
from .logger import get_logger
from .models import DataAgentOutput, ExecutionMetadata, QualityIssue, QualityReport, SchemaInformation, ValidationSummary
from .normalization import DataNormalizer
from .postgres import DatabaseUnavailable, PostgreSQLConnector, QueryExecutionError
from .validation import DataValidator


class DataAgent:
    def __init__(self, settings: DataAgentSettings, *, connector: PostgreSQLConnector | None = None, custom_handlers: dict[str, CustomHandler] | None = None) -> None:
        self.settings = settings
        self.connector = connector or PostgreSQLConnector(settings)
        self.validator = DataValidator(settings, self.connector)
        self.cleaner = DataCleaner(settings, custom_handlers)
        self.normalizer = DataNormalizer(settings)
        self.logger = get_logger(settings.log_level)

    def run(self, *, organization_id: str, request_id: str | None = None, query_parameters: dict[str, Any] | None = None) -> DataAgentOutput:
        request_id = request_id or str(uuid4())
        started = datetime.now(timezone.utc)
        started_clock = time.perf_counter()
        frames: list[pd.DataFrame] = []
        batches = 0
        rows_read = 0
        warnings: list[str] = []
        errors: list[str] = []
        transformations: list[str] = []
        issues: list[QualityIssue] = []
        validation = ValidationSummary(valid=False, required_columns=[column for column, rule in self.settings.schema_rules.items() if rule.required])
        schema = SchemaInformation(columns={}, nullable_counts={}, primary_keys=[])
        source_name = self.settings.source.table or "configured_query"
        try:
            query, parameters = self.connector.source_query(self.settings.source, organization_id, query_parameters)
            self.logger.info("query_started", extra={"request_id": request_id, "operation": "load"})
            for batch in self.connector.stream_frames(query, parameters, self.settings.source.batch_size):
                batches += 1; rows_read += len(batch)
                frames.append(batch)
                self.logger.info("batch_loaded", extra={"request_id": request_id, "batch": batches, "row_count": len(batch)})
            if not frames:
                warnings.append("The configured source returned no rows")
                frame = pd.DataFrame(columns=list(self.settings.schema_rules))
            else:
                frame = pd.concat(frames, ignore_index=True)
            frame, validation, schema, issues = self.validator.validate(frame)
            detected_issues = list(issues)
            frame, cleaning_steps, rows_dropped, duplicate_rows = self.cleaner.clean(frame)
            frame, normalization_steps = self.normalizer.normalize(frame)
            frame, validation, schema, remaining_issues = self.validator.validate(frame)
            transformations.extend(cleaning_steps + normalization_steps)
            invalid_cells = sum(issue.affected_rows for issue in detected_issues if issue.code not in {"missing_column", "unexpected_columns"})
            missing_cells = int(frame.isna().sum().sum())
            denominator = max(1, frame.size)
            score = max(0.0, round(100 - ((missing_cells + invalid_cells + duplicate_rows) / denominator * 100), 2))
            quality = QualityReport(score=score, missing_cells=missing_cells, duplicate_rows=duplicate_rows, invalid_cells=invalid_cells, issues=detected_issues)
            errors.extend(issue.message for issue in remaining_issues if issue.severity == "error")
            warnings.extend(issue.message for issue in detected_issues if issue.severity == "warning")
            cleaned = self._serialize(frame)
            success = validation.valid and not errors
        except (DatabaseUnavailable, QueryExecutionError, ValueError, MemoryError) as exc:
            self.logger.exception("data_agent_failed", extra={"request_id": request_id, "operation": "pipeline"})
            errors.append(str(exc) or exc.__class__.__name__)
            rows_dropped = 0
            frame = pd.DataFrame()
            quality = QualityReport(score=0, issues=[QualityIssue(severity="error", code=exc.__class__.__name__, message=errors[-1])])
            cleaned = []
            success = False
        except Exception as exc:  # defensive workflow boundary
            self.logger.exception("unexpected_data_agent_failure", extra={"request_id": request_id, "operation": "pipeline"})
            errors.append(f"Unexpected data-agent failure: {exc}")
            rows_dropped = 0; frame = pd.DataFrame(); quality = QualityReport(score=0, issues=[QualityIssue(severity="error", code="unexpected_error", message=errors[-1])]); cleaned = []; success = False
        completed = datetime.now(timezone.utc)
        elapsed = round(time.perf_counter() - started_clock, 6)
        metadata = ExecutionMetadata(request_id=request_id, organization_id=organization_id, source=source_name, started_at=started, completed_at=completed, batches_processed=batches, rows_read=rows_read, rows_dropped=rows_dropped, transformations=transformations, downstream_agents=self.settings.downstream_agents)
        self.logger.info("pipeline_completed", extra={"request_id": request_id, "operation": "pipeline", "duration_ms": round(elapsed * 1000), "row_count": len(frame)})
        return DataAgentOutput(success=success, cleaned_data=cleaned, validation_summary=validation, quality_report=quality, schema_information=schema, metadata=metadata, execution_time_seconds=elapsed, row_count=len(frame), column_count=len(frame.columns), warnings=warnings, errors=errors)

    def run_dataframe(self, *, organization_id: str, request_id: str | None = None, query_parameters: dict[str, Any] | None = None) -> tuple[pd.DataFrame, DataAgentOutput]:
        """Return a DataFrame for Python/ML consumers alongside the serializable audit result."""
        output = self.run(organization_id=organization_id, request_id=request_id, query_parameters=query_parameters)
        if isinstance(output.cleaned_data, list): frame = pd.DataFrame(output.cleaned_data)
        elif isinstance(output.cleaned_data, dict): frame = pd.DataFrame(output.cleaned_data)
        else: frame = pd.DataFrame(json.loads(output.cleaned_data)) if output.cleaned_data else pd.DataFrame()
        return frame, output

    def _serialize(self, frame: pd.DataFrame):
        safe = frame.astype(object).where(pd.notna(frame), None)
        if self.settings.output_format == "columns": return safe.to_dict(orient="list")
        records = safe.to_dict(orient="records")
        if self.settings.output_format == "json": return json.dumps(records, default=str, ensure_ascii=False)
        return json.loads(json.dumps(records, default=str, ensure_ascii=False))
