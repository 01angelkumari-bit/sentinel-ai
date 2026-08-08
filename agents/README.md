# Sentinel AI agents

The Data Agent is the governed entry point for structured data entering Sentinel AI's multi-agent workflow. It reads PostgreSQL through a pooled SQLAlchemy connector, validates and cleans data, generates an auditable quality report, and distributes one consistent typed envelope to downstream agents.

## Run the Data Agent

Set `DATABASE_URL`, copy `config/data_agent.example.yaml`, and adjust the source/schema rules. Credentials belong only in environment variables.

```powershell
$env:DATABASE_URL='postgresql+psycopg://sentinel:password@localhost:5432/sentinel'
backend\.venv-win\Scripts\python.exe -c "from agents.data_agent import DataAgentSettings, build_data_workflow; settings=DataAgentSettings.from_yaml('agents/config/data_agent.example.yaml'); print(build_data_workflow(settings).invoke({'request_id':'manual-run','organization_id':'YOUR-ORGANIZATION-UUID'}))"
```

The compiled graph executes:

```text
START -> data_agent -> distribute -> END
```

The `distribution` state contains the same cleaned dataset, quality report, validation summary, request ID, and mandatory organization ID for the analytics, report, visualization, ML, recommendation, PDF, and dashboard consumers. PostgreSQL streams also set the RLS tenant context before executing SQL.

## Capabilities

- Full table, parameterized query, incremental, limited, and chunked reads.
- Connection pooling, pre-ping, reconnect retries, statement/connect timeouts, and transactions.
- Required/unexpected column, type, range, regex, primary-key, and foreign-key validation.
- Missing-value strategies per column, including registered custom handlers.
- Text, Unicode, date, currency, phone, and email normalization.
- Min-max, standard/Z-score, label, and one-hot feature preparation.
- Records, column-oriented dictionary, and JSON outputs.
- JSON structured logs with request and batch correlation.
- Failure-safe LangGraph state: operational errors become typed `errors` and stop downstream distribution.

Run tests from the repository root:

```powershell
backend\.venv-win\Scripts\python.exe -m pytest agents\tests -q
```
