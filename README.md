# Sentinel AI

Sentinel AI is a Windows-native, enterprise Business Intelligence platform that combines governed AI-agent workflows, normalized operational data, secure authentication, and an executive command center.

The repository includes a Next.js dashboard, FastAPI backend, SQLAlchemy data layer, Alembic migrations, deterministic Faker datasets, and PowerShell automation for setup and process management.

## What Sentinel AI provides

- Secure registration and login with Argon2 password hashing and JWT authentication.
- Protected B2B dashboard with executive metrics, signal monitoring, and insight panels.
- Responsive enterprise interface built with Next.js, Tailwind CSS, and shadcn/ui conventions.
- Normalized 3NF business schema covering customers, products, sales, inventory, finance, employees, suppliers, support, warehouses, and reports.
- PostgreSQL-ready SQLAlchemy models with Alembic migrations.
- Native SQLite development database for immediate Windows setup.
- Deterministic Faker seed generation and relational CSV exports.
- Windows PowerShell scripts for installation, startup, health checks, logging, and shutdown.

## Technology stack

| Layer | Technology |
|---|---|
| Web application | Next.js 15 App Router, React 19, TypeScript |
| UI | Tailwind CSS, shadcn/ui conventions, Lucide icons |
| API | FastAPI, Pydantic |
| ORM and migrations | SQLAlchemy 2, Alembic |
| Development database | SQLite |
| Production database | PostgreSQL |
| Authentication | JWT, Argon2, HttpOnly cookies |
| Synthetic data | Faker, deterministic Python generator |
| Local automation | Windows PowerShell |

## Repository structure

```text
sentinel-ai/
├── frontend/                Next.js dashboard and authentication UI
├── backend/                 FastAPI application and Alembic migrations
│   ├── app/api/             Versioned routes and authentication dependencies
│   ├── app/application/     Business use cases and services
│   ├── app/domain/          User and BI SQLAlchemy models
│   └── app/infrastructure/  Database engine and sessions
├── agents/                  Agent contracts and governance boundary
├── database/                Database documentation and model surface
├── synthetic_data/          Faker seed generator and generated CSV files
├── scripts/windows/         Native Windows setup/start/stop scripts
└── docs/                    Architecture, Windows runbook, and ER diagram
```

## Windows prerequisites

Sentinel AI runs natively on Windows. Docker, WSL, Bash, and Linux containers are not required.

Install:

- Python 3.12 with the Python Launcher enabled.
- Node.js 22 LTS.
- Git for Windows.

Confirm the tools are available:

```powershell
py -3.12 --version
node --version
npm --version
git --version
```

## Quick start

Open PowerShell in the project directory.

### 1. Configure the environment

```powershell
Copy-Item .env.windows.example .env
```

Edit `.env` and replace `JWT_SECRET_KEY` with a random value containing at least 32 characters. The local database is configured as:

```env
DATABASE_URL=sqlite:///./sentinel.db
```

Do not commit `.env`. It is already ignored by Git.

### 2. Install dependencies and migrate the database

```powershell
.\scripts\windows\setup.ps1
```

This command creates the Python 3.12 virtual environment, installs backend and frontend dependencies, and runs every Alembic migration.

### 3. Start Sentinel AI

```powershell
.\scripts\windows\start.ps1 -SkipSetup
```

Open:

- Application: [http://localhost:3000](http://localhost:3000)
- API health: [http://localhost:8000/health](http://localhost:8000/health)
- Interactive API documentation: [http://localhost:8000/docs](http://localhost:8000/docs)

### 4. Create an account

1. Open the application.
2. Select **Create an account**.
3. Enter your name, work email, password, and matching confirmation password.
4. Sign in to access the protected command center.

### 5. Stop Sentinel AI

```powershell
.\scripts\windows\stop.ps1
```

Application logs are written to the ignored `.sentinel` directory.

## Business Intelligence database

The schema follows third normal form. Business entities and reusable classifications are stored once, while junction and transaction tables represent operational relationships.

Major domains include:

- Customers and support history.
- Product catalog and normalized categories.
- Supplier sourcing with lead times and preferred-vendor status.
- Sales order headers and line items.
- Warehouse inventory balances and audited movements.
- Employees, departments, and manager hierarchies.
- Finance accounts and transactions linked to originating sales orders.
- Configurable business reports and schedules.

See [the ER diagram](docs/er-diagram.md) for the complete relationship model.

## Synthetic datasets

The included generator uses a fixed seed, so generated identifiers and relationships are repeatable.

Current reference dataset:

| Dataset | Rows |
|---|---:|
| Sales coverage | 365 consecutive days |
| Customers | 500 |
| Products | 100 |
| Employees | 200 |
| Suppliers | 50 |
| Warehouses | 10 |
| Sales orders | 1,609 |
| Sales line items | 4,814 |
| Support tickets | 900 |
| Finance transactions | 1,516 |

Generate fresh CSV files:

```powershell
backend\.venv-win\Scripts\python.exe synthetic_data\seed.py
```

Regenerate CSVs and replace the local BI seed data:

```powershell
backend\.venv-win\Scripts\python.exe synthetic_data\seed.py --database --reset
```

Never use `--reset` against a production database.

## PostgreSQL production configuration

SQLite is used only to simplify local Windows development. For production, provision PostgreSQL, update `DATABASE_URL`, and apply migrations:

```env
DATABASE_URL=postgresql+psycopg://sentinel:strong-password@database-host:5432/sentinel
```

```powershell
cd backend
.\.venv-win\Scripts\python.exe -m alembic upgrade head
```

Use a managed secret store for database credentials and JWT signing keys.

## API layout

The current authentication API is versioned under `/api/v1`:

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/api/v1/auth/register` | Create a user account |
| `POST` | `/api/v1/auth/login` | Issue an access token |
| `GET` | `/api/v1/auth/me` | Return the authenticated user |
| `GET` | `/api/v1/dashboard/summary` | Return live executive KPIs, chart series, alerts, and recommendations |
| `GET` | `/api/v1/sales` | Paginated sales orders and revenue trend |
| `GET` | `/api/v1/finance` | Paginated ledger transactions and account balances |
| `GET` | `/api/v1/inventory` | Paginated warehouse-product availability |
| `GET` | `/api/v1/support` | Paginated support tickets and status distribution |
| `GET` | `/api/v1/employees` | Paginated workforce directory and department distribution |
| `GET` | `/api/v1/customers` | Paginated customer accounts and regional distribution |
| `GET` | `/health` | Operational health check |

Protected endpoints validate bearer tokens through a shared FastAPI dependency. The frontend exchanges the access token for an HttpOnly, SameSite session cookie.

The six business endpoints return a consistent Recharts-ready envelope containing `items`, `pagination`, and `chart_data` (`label`/`value` points). Each supports validated `page`, `page_size`, `sort_by`, and `sort_order` parameters plus domain-specific filters. Page size is capped at 100, and sorting is restricted to explicit safe columns. See the interactive Swagger documentation for the complete filter contract.

The executive dashboard calculates revenue, profit, cash balance, open support cases, workforce totals, regional performance, top products, and customer sentiment directly from the normalized BI database. Visualizations are rendered with Recharts and do not rely on hardcoded KPI values.

## Development commands

Backend development server:

```powershell
cd backend
.\.venv-win\Scripts\python.exe -m uvicorn app.main:app --reload
```

Frontend development server:

```powershell
cd frontend
npm run dev
```

Frontend production validation:

```powershell
cd frontend
npm run build
```

Apply migrations:

```powershell
cd backend
.\.venv-win\Scripts\python.exe -m alembic upgrade head
```

## Security baseline

- Passwords are hashed with Argon2 and never stored as plaintext.
- JWT access tokens are short lived and signed with a configurable secret.
- Browser tokens are stored in HttpOnly cookies instead of local storage.
- Protected pages are gated by Next.js middleware and revalidated by the API.
- Database credentials and signing secrets are excluded from version control.

Before a public production launch, add TLS termination, secret rotation, rate limiting, audit-event persistence, backup policies, dependency scanning, and a managed identity provider.

## Troubleshooting

### The site does not open

Check the runtime logs:

```powershell
Get-Content .sentinel\backend-error.log
Get-Content .sentinel\frontend-error.log
```

Restart the services:

```powershell
.\scripts\windows\stop.ps1
.\scripts\windows\start.ps1 -SkipSetup
```

### Dependencies are missing

Run the complete setup again:

```powershell
.\scripts\windows\setup.ps1
```

### Database schema is outdated

```powershell
cd backend
.\.venv-win\Scripts\python.exe -m alembic upgrade head
```

## Documentation

- [Architecture](docs/architecture.md)
- [Native Windows runbook](docs/windows.md)
- [Database ER diagram](docs/er-diagram.md)
- [Synthetic data guide](synthetic_data/README.md)
- [Database operations](database/README.md)

## Roadmap

- Live dashboard APIs backed by BI aggregation queries.
- Dataset upload and validation workflows.
- Governed agent orchestration and execution audit logs.
- Role-based access control and multi-tenant workspaces.
- Scheduled reports and alert delivery.
- Data-source connectors for ERP, CRM, finance, and support platforms.
- Automated tests and continuous integration.

## License

No open-source license has been selected yet. Add an approved license before external redistribution.
