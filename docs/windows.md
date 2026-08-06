# Native Windows runbook

Sentinel AI runs as native Windows processes. SQLite provides local persistence, FastAPI runs from a Python 3.12 virtual environment, and Next.js runs under Node.js. Docker Desktop, WSL, Linux images, and a separate database service are not part of this runtime path.

## Prerequisites

Verify installations from PowerShell:

```powershell
python --version
node --version
npm --version
```

## Commands

- `scripts\windows\setup.ps1` validates configuration, installs dependencies, creates the database, and applies Alembic migrations.
- `scripts\windows\start.ps1` starts the API and web application in the background.
- `scripts\windows\stop.ps1` stops only the processes recorded by Sentinel AI.

If startup fails, inspect `.sentinel\backend-error.log` and `.sentinel\frontend-error.log`.

For a production PostgreSQL deployment, set `DATABASE_URL` to a native Windows PostgreSQL connection string and rerun Alembic migrations.
