from __future__ import annotations

import re
import time
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from typing import Any

import pandas as pd
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import DBAPIError, OperationalError, SQLAlchemyError

from .config import DataAgentSettings, SourceConfig

IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class DatabaseUnavailable(RuntimeError):
    pass


class QueryExecutionError(RuntimeError):
    pass


class PostgreSQLConnector:
    """Pooled SQLAlchemy connector supporting PostgreSQL and SQLite-based tests."""

    def __init__(self, settings: DataAgentSettings) -> None:
        self.settings = settings
        options: dict[str, Any] = {"pool_pre_ping": True, "pool_recycle": 1_800}
        if settings.database_url.startswith("postgresql"):
            options.update(pool_size=settings.pool_size, max_overflow=settings.max_overflow, pool_timeout=settings.pool_timeout_seconds)
            options["connect_args"] = {"connect_timeout": min(settings.pool_timeout_seconds, 30), "options": f"-c statement_timeout={settings.statement_timeout_seconds * 1000}"}
        elif settings.database_url.startswith("sqlite"):
            options["connect_args"] = {"check_same_thread": False}
        self.engine: Engine = create_engine(settings.database_url, **options)

    def close(self) -> None:
        self.engine.dispose()

    def healthcheck(self) -> None:
        self._with_reconnect(lambda connection: connection.execute(text("SELECT 1")).scalar_one())

    @contextmanager
    def transaction(self) -> Iterator[Connection]:
        try:
            with self.engine.begin() as connection:
                yield connection
        except SQLAlchemyError as exc:
            raise QueryExecutionError("Database transaction failed") from exc

    def execute_frame(self, query: str, parameters: Mapping[str, Any] | None = None) -> pd.DataFrame:
        return self._with_reconnect(lambda connection: pd.read_sql_query(text(query), connection, params=dict(parameters or {})))

    def stream_frames(self, query: str, parameters: Mapping[str, Any] | None, batch_size: int) -> Iterator[pd.DataFrame]:
        attempts = self.settings.reconnect_attempts
        yielded_any = False
        for attempt in range(1, attempts + 1):
            try:
                with self.engine.connect().execution_options(stream_results=True) as connection:
                    if connection.dialect.name == "postgresql":
                        organization_id = str((parameters or {}).get("_organization_id", ""))
                        if not organization_id:
                            raise QueryExecutionError("organization_id is required before opening an agent data stream")
                        connection.execute(text("SELECT set_config('app.current_organization', :organization_id, true)"), {"organization_id": organization_id})
                    for frame in pd.read_sql_query(text(query), connection, params=dict(parameters or {}), chunksize=batch_size):
                        yielded_any = True
                        yield frame
                return
            except (OperationalError, DBAPIError) as exc:
                if yielded_any:
                    raise DatabaseUnavailable("Database connection was interrupted after a partial batch transfer; retry the request with the same incremental cursor") from exc
                if attempt == attempts:
                    raise DatabaseUnavailable(f"Database unavailable after {attempts} attempts") from exc
                self.engine.dispose()
                time.sleep(min(2 ** (attempt - 1), 8))
            except SQLAlchemyError as exc:
                raise QueryExecutionError("Query execution failed") from exc

    def source_query(self, source: SourceConfig, organization_id: str, runtime_parameters: Mapping[str, Any] | None = None) -> tuple[str, dict[str, Any]]:
        if not organization_id:
            raise QueryExecutionError("organization_id is required for every Data Agent query")
        parameters = {**source.query_parameters, **dict(runtime_parameters or {})}
        if source.query:
            query = source.query.strip().rstrip(";")
            if not query.lower().startswith(("select ", "with ")):
                raise QueryExecutionError("Only SELECT or WITH queries are allowed for data loading")
        else:
            table = self._identifier(source.table or "", "table")
            columns = ", ".join(self._identifier(column, "column") for column in source.columns) if source.columns else "*"
            query = f"SELECT {columns} FROM {table}"
        query = f"SELECT * FROM ({query}) AS tenant_source WHERE organization_id = :_organization_id"
        parameters["_organization_id"] = organization_id
        if source.incremental_column and source.incremental_value is not None:
            incremental = self._identifier(source.incremental_column, "incremental column")
            query = f"SELECT * FROM ({query}) AS source_data WHERE {incremental} > :_incremental_value"
            parameters["_incremental_value"] = source.incremental_value
        query = f"SELECT * FROM ({query}) AS bounded_source LIMIT {int(source.max_rows)}"
        return query, parameters

    def _with_reconnect(self, operation):
        for attempt in range(1, self.settings.reconnect_attempts + 1):
            try:
                with self.engine.connect() as connection:
                    return operation(connection)
            except (OperationalError, DBAPIError) as exc:
                if attempt == self.settings.reconnect_attempts:
                    raise DatabaseUnavailable(f"Database unavailable after {attempt} attempts") from exc
                self.engine.dispose()
                time.sleep(min(2 ** (attempt - 1), 8))
            except SQLAlchemyError as exc:
                raise QueryExecutionError("Query execution failed") from exc

    @staticmethod
    def _identifier(value: str, label: str) -> str:
        if not IDENTIFIER.fullmatch(value):
            raise QueryExecutionError(f"Invalid {label} identifier: {value!r}")
        return value
