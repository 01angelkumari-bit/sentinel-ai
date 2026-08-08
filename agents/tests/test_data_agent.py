from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from sqlalchemy import create_engine, text

from agents.data_agent.agent import DataAgent
from agents.data_agent.cleaning import DataCleaner
from agents.data_agent.config import CleaningRule, ColumnSchema, DataAgentSettings, MissingValueRule, NormalizationRule, SourceConfig
from agents.data_agent.normalization import DataNormalizer
from agents.data_agent.postgres import PostgreSQLConnector, QueryExecutionError
from agents.data_agent.validation import DataValidator
from agents.data_agent.workflow import build_data_workflow


@pytest.fixture()
def database_url(tmp_path: Path) -> str:
    path = tmp_path / "agent.db"
    engine = create_engine(f"sqlite:///{path.as_posix()}")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE customers (id INTEGER, organization_id TEXT, name TEXT, email TEXT, phone TEXT, revenue TEXT, region TEXT, created_at TEXT)"))
        connection.execute(text("INSERT INTO customers VALUES (1, 'org-a', '  acme corp  ', ' SALES@ACME.COM ', '(212) 555-0100', '$100.00', 'north', '2026-01-01'), (2, 'org-a', 'Beta ltd', NULL, 'invalid', '$300.00', 'south', '2026-01-02'), (2, 'org-a', 'Beta ltd', NULL, 'invalid', '$300.00', 'south', '2026-01-02'), (3, 'org-b', 'Private Co', 'private@example.com', '+12125550199', '$999.00', 'west', '2026-01-03')"))
    engine.dispose()
    return f"sqlite:///{path.as_posix()}"


@pytest.fixture()
def settings(database_url: str) -> DataAgentSettings:
    return DataAgentSettings(
        database_url=database_url,
        source=SourceConfig(table="customers", batch_size=100, max_rows=1000),
        schema_rules={
            "id": ColumnSchema(type="integer", required=True, nullable=False, primary_key=True),
            "organization_id": ColumnSchema(type="string", required=True, nullable=False),
            "name": ColumnSchema(type="string", required=True, nullable=False),
            "email": ColumnSchema(type="email", required=True, nullable=False, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$"),
            "phone": ColumnSchema(type="phone", nullable=True),
            "revenue": ColumnSchema(type="currency", required=True, nullable=False, minimum=0),
            "region": ColumnSchema(type="string", required=True, nullable=False),
            "created_at": ColumnSchema(type="date", required=True, nullable=False),
        },
        missing_values={"email": MissingValueRule(strategy="constant", value="unknown@example.com"), "phone": MissingValueRule(strategy="constant", value="+10000000000")},
        cleaning={"name": CleaningRule(titlecase=True), "email": CleaningRule(lowercase=True), "region": CleaningRule(titlecase=True)},
        normalization={},
        allow_unexpected_columns=False,
    )


def test_connector_health_and_streaming(settings: DataAgentSettings) -> None:
    connector = PostgreSQLConnector(settings)
    connector.healthcheck()
    query, parameters = connector.source_query(settings.source, "org-a")
    chunks = list(connector.stream_frames(query, parameters, 100))
    assert sum(len(chunk) for chunk in chunks) == 3
    connector.close()


def test_connector_rejects_unsafe_identifier(settings: DataAgentSettings) -> None:
    settings.source = SourceConfig(table="customers; DROP TABLE customers", batch_size=100)
    with pytest.raises(QueryExecutionError, match="Invalid table identifier"):
        PostgreSQLConnector(settings).source_query(settings.source, "org-a")


def test_validation_reports_primary_key_and_null_issues(settings: DataAgentSettings) -> None:
    connector = PostgreSQLConnector(settings)
    frame = connector.execute_frame("SELECT * FROM customers WHERE organization_id = 'org-a'")
    _, summary, _, issues = DataValidator(settings, connector).validate(frame)
    assert summary.primary_key_valid is False
    assert {issue.code for issue in issues} >= {"invalid_primary_key", "null_not_allowed"}


def test_cleaning_normalizes_and_imputes(settings: DataAgentSettings) -> None:
    frame = pd.DataFrame({"name": ["  acme corp  "], "email": [None], "phone": ["212-555-0100"], "region": ["north"]})
    cleaned, steps, _, _ = DataCleaner(settings).clean(frame)
    assert cleaned.loc[0, "name"] == "Acme Corp"
    assert cleaned.loc[0, "email"] == "unknown@example.com"
    assert cleaned.loc[0, "phone"] == "+12125550100"
    assert cleaned.loc[0, "region"] == "North"
    assert steps


def test_custom_missing_handler(settings: DataAgentSettings) -> None:
    settings.missing_values = {"region": MissingValueRule(strategy="custom", custom_handler="fallback", value="Unknown")}
    cleaner = DataCleaner(settings, {"fallback": lambda series, value: series.fillna(value)})
    cleaned, _, _, _ = cleaner.clean(pd.DataFrame({"region": [None]}))
    assert cleaned.loc[0, "region"] == "Unknown"


def test_normalization_and_encoding(settings: DataAgentSettings) -> None:
    settings.normalization = {"revenue": NormalizationRule(method="min_max"), "region": NormalizationRule(method="one_hot")}
    frame, steps = DataNormalizer(settings).normalize(pd.DataFrame({"revenue": [10, 20, 30], "region": ["N", "S", "N"]}))
    assert frame["revenue"].tolist() == [0.0, 0.5, 1.0]
    assert {"region_N", "region_S"}.issubset(frame.columns)
    assert len(steps) == 2


def test_agent_returns_typed_failure_without_crashing(settings: DataAgentSettings) -> None:
    settings.source = SourceConfig(query="DELETE FROM customers", batch_size=100)
    output = DataAgent(settings).run(organization_id="org-a", request_id="failure-test")
    assert output.success is False
    assert output.errors
    assert output.metadata.request_id == "failure-test"


def test_agent_and_langgraph_distribution(settings: DataAgentSettings) -> None:
    settings.schema_rules["id"].primary_key = False
    output = DataAgent(settings).run(organization_id="org-a", request_id="agent-test")
    assert output.row_count == 2
    assert output.column_count == 8
    assert output.cleaned_data[0]["name"] == "Acme Corp"
    assert output.quality_report.duplicate_rows == 1
    frame, frame_output = DataAgent(settings).run_dataframe(organization_id="org-a", request_id="frame-test")
    assert isinstance(frame, pd.DataFrame) and len(frame) == frame_output.row_count
    graph = build_data_workflow(settings)
    state = graph.invoke({"request_id": "graph-test", "organization_id": "org-a"})
    assert state["data_agent_output"]["metadata"]["request_id"] == "graph-test"
    assert set(state["distribution"]) == set(settings.downstream_agents)
    assert state["distribution"]["analytics"]["cleaned_data"] == state["distribution"]["pdf"]["cleaned_data"]
    assert all(row["organization_id"] == "org-a" for row in state["cleaned_data"])

def test_data_agent_rejects_missing_tenant(settings: DataAgentSettings) -> None:
    with pytest.raises(QueryExecutionError, match="organization_id is required"):
        PostgreSQLConnector(settings).source_query(settings.source, "")
