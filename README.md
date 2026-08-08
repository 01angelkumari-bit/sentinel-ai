# Sentinel AI

Sentinel AI is a Windows-first, multi-tenant Business Intelligence platform. Organizations upload their own CSV or Excel data, receive tenant-isolated dashboards and PDF reports, and ask a data-aware assistant questions about verified business metrics, risks, anomalies, and recommendations.

The application does not load a shared demo database. A new authenticated session starts with an empty analysis workspace, and uploaded data, generated reports, and session-specific AI conversations are cleared when that session ends. Permanent accounts, organizations, roles, audit records, invitations, and report schedules remain intact.

![Sentinel AI authentication experience](docs/screenshots/authentication-hero.png)

## Hosted architecture

| Layer | Production service |
|---|---|
| Frontend | Vercel |
| Backend | Render |
| Database | Neon PostgreSQL |
| Uploads and reports | Render ephemeral storage on free tier; persistent disk when upgraded |

See the [deployment runbook](docs/deployment.md), [architecture diagrams](docs/architecture.md),
[screenshots](docs/screenshots), [demo video](docs/demo/sentinel-ai-demo.avi), and
[resume bullet points](docs/resume-bullets.md).

## Features

- Real email registration, OTP login, and password recovery through SMTP.
- JWT authentication with revocable server-side sessions and HttpOnly cookies.
- Organization isolation, role-based access control, and PostgreSQL row-level security migrations.
- Roles: `owner`, `admin`, `manager`, `employee`, and `viewer`.
- CSV/XLSX onboarding with validation, preview, batch import, append/replace modes, progress, and history.
- Executive KPIs, revenue trends, regional performance, products, alerts, and recommendations.
- Protected CSV export and detailed, persisted PDF reports with view/download endpoints.
- Sentinel AI multi-turn chat with deterministic calculations over the active tenant dataset.
- Evidence-backed revenue, concentration, cancellation, anomaly, and data-quality risk analysis.
- Optional rating or feedback sentiment analysis through the open-source VADER model.
- Self-hostable Hugging Face model adapter; no paid AI API is required.
- LangGraph Data Agent with PostgreSQL loading, validation, cleaning, normalization, and typed state.
- Native Windows setup, start, stop, migration, logging, and test workflows.

## Technology

| Area | Stack |
|---|---|
| Frontend | Next.js 15 App Router, React 19, TypeScript |
| UI | Tailwind CSS, shadcn/ui conventions, Lucide, Recharts |
| Backend | FastAPI, Pydantic, Pandas |
| Persistence | PostgreSQL or local SQLite, SQLAlchemy 2, Alembic |
| Authentication | JWT, Argon2, real SMTP OTP |
| AI | Deterministic analytics, VADER, optional local Hugging Face model |
| Agents | LangGraph, typed workflow state |
| Reports | ReportLab PDF generation |
| Tests | Pytest, Next.js production build, TypeScript |

## Project structure

```text
Sentinel AI/
|-- frontend/               Next.js application and server-side API relays
|-- backend/                FastAPI application, domain models, services, tests
|   |-- alembic/            Versioned database migrations
|   `-- app/
|       |-- api/            REST routes, validation, auth dependencies
|       |-- application/    Auth, analytics, AI, imports, reports
|       |-- domain/         SQLAlchemy business and user models
|       |-- repositories/   Tenant-filtered database access
|       `-- infrastructure/ Database engine and sessions
|-- agents/                 LangGraph Data Agent and tests
|-- database/               Database documentation
|-- synthetic_data/         Faker generators and CSV exports
|-- docs/                   Architecture, ER diagram, Windows runbook
|-- scripts/windows/        Native setup/start/stop scripts
`-- docker/                 Reserved; Docker is not required for Windows
```

## Windows prerequisites

Install these applications and enable their PATH options:

- Windows 10 or Windows 11
- Python 3.12 with the Python Launcher (`py`)
- Node.js 22 LTS and npm
- Git for Windows
- Optional: PostgreSQL 16+ for a production-like local database
- Optional: a locally hosted Hugging Face inference server

Verify them in PowerShell:

```powershell
py -3.12 --version
node --version
npm --version
git --version
```

Docker Desktop, WSL, Bash, and Linux containers are not required.

## Quick start on Windows

### 1. Clone and enter the repository

```powershell
git clone https://github.com/01angelkumari-bit/sentinel-ai.git
cd sentinel-ai
```

### 2. Create the local environment file

```powershell
Copy-Item .env.windows.example .env
```

Generate a secure JWT signing key:

```powershell
$bytes = New-Object byte[] 48
[Security.Cryptography.RandomNumberGenerator]::Fill($bytes)
[Convert]::ToBase64String($bytes)
```

Copy the generated value into `JWT_SECRET_KEY` in `.env`. Never commit `.env` or paste real credentials into issues, commits, screenshots, or chat messages.

For the easiest local database, keep:

```env
DATABASE_URL=sqlite:///./sentinel.db
```

### 3. Configure real SMTP email

Registration and password recovery require real email delivery. For Gmail development:

1. Enable two-step verification on the sending Google account.
2. Create a Google App Password named `Sentinel AI`.
3. Configure `.env`:

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=sender@gmail.com
SMTP_PASSWORD=your-16-character-app-password
SMTP_USE_TLS=true
SMTP_USE_SSL=false
EMAIL_FROM=sender@gmail.com
```

Use the App Password, not the normal Gmail password. For production, use a transactional provider and authenticate the sending domain with SPF and DKIM. SendGrid SMTP uses `smtp.sendgrid.net`, port `587`, username `apikey`, and the API key as `SMTP_PASSWORD`.

### 4. Install dependencies and migrate

Run PowerShell from the repository root:

```powershell
.\scripts\windows\setup.ps1
```

The script:

- creates `backend\.venv-win`;
- installs Python dependencies;
- installs frontend npm dependencies;
- applies every Alembic migration.

### 5. Start the application

```powershell
.\scripts\windows\start.ps1 -SkipSetup
```

Open:

- Web application: <http://localhost:3000>
- Login: <http://localhost:3000/login>
- API documentation: <http://localhost:8000/docs>
- Health endpoint: <http://localhost:8000/health>

Runtime PID files and logs are written to the ignored `.sentinel` directory.

### 6. Stop the application

```powershell
.\scripts\windows\stop.ps1
```

## First-use workflow

1. Open `/register`.
2. Enter organization name, full name, real email, password, and confirmation.
3. Retrieve the six-character letter-and-number OTP from the mailbox.
4. Verify the OTP and sign in.
5. A new login opens an empty, private analysis workspace.
6. Upload a valid CSV or XLSX file on the onboarding page.
7. Wait for validation and import completion.
8. Open the generated dashboard, ask Sentinel questions, or export a PDF.
9. Sign out to revoke the token and clear session-only datasets, reports, files, caches, and AI context.

## Dataset format

Every import must contain these core columns:

```csv
Date,Revenue,Orders,Cancelled,Region,Product,Customer
2026-08-01,250000,25,2,North,Sentinel Core,Acme Corporation
```

Rules:

- `Date` must be a valid date.
- `Revenue`, `Orders`, and `Cancelled` must be numeric.
- Values cannot be negative.
- `Cancelled` cannot exceed `Orders`.
- `Region`, `Product`, and `Customer` cannot be empty.
- Files must be UTF-8 CSV or valid XLSX.
- The default upload limit is 10 MB and 100,000 records per import.

Optional columns are preserved for structured analysis. Customer sentiment is available only when a supported column exists, such as:

```csv
Rating,Feedback
5,Excellent service and a reliable product
```

Recognized rating names include `Rating`, `Stars`, `Review Score`, and `Satisfaction Score`. Recognized text names include `Feedback`, `Review`, `Comment`, and related normalized variants. If neither exists, Sentinel reports that sentiment is unavailable; it does not generate a default score.

Import modes:

- `initial`: allowed only when the current session has no dataset.
- `append`: adds validated records to the active dataset.
- `replace`: removes the current temporary business dataset and imports the new one.

## Sentinel AI

Sentinel routes questions by intent:

- normal conversation: greetings, thanks, and capabilities;
- website help: onboarding, dashboards, login, files, and reports;
- structured data: exact totals, averages, rankings, trends, and comparisons;
- risks: decline, volatility, concentration, cancellations, anomalies, and data quality;
- sentiment: rating normalization or VADER analysis of feedback text;
- report questions: protected report and metric guidance.

Structured calculations run in Python/Pandas or tenant-filtered SQL. The language model is never trusted to calculate business numbers.

Example questions:

```text
Hi
Summarize my data.
What is total revenue?
Which region performed worst?
Which product performed best?
What are the biggest risks?
What evidence supports that conclusion?
Give me recommendations.
What is my customer sentiment?
```

### Optional self-hosted model

Sentinel works without an LLM. To enable natural-language rewriting, host an open-source Hugging Face instruction model through an OpenAI-compatible local server such as vLLM or llama.cpp:

```env
AI_PROVIDER=local_hf
AI_MODEL_ID=Qwen/Qwen2.5-3B-Instruct
AI_BASE_URL=http://localhost:8080
AI_REQUEST_TIMEOUT_SECONDS=45
```

If the model is unavailable, Sentinel returns the deterministic verified response rather than inventing an answer.

## Session and tenant security

- Every JWT carries user, organization, role, JTI, issue time, and expiry claims.
- Every protected request validates the JTI against a non-revoked server-side session.
- Business records, imports, files, conversations, reports, and analytics are organization-filtered.
- Direct cross-tenant resource IDs return `404` or `401` as appropriate.
- PostgreSQL RLS migrations provide defense in depth.
- Browser tokens remain in HttpOnly, SameSite cookies.
- Logout revokes the server session and clears browser storage/cache.
- A successful fresh login clears the previous temporary analysis workspace.
- Permanent identity, RBAC, invitations, schedules, and audit records are not deleted on logout.
- Uploaded names are sanitized, stored names are unique, and resolved paths are constrained to `STORAGE_ROOT`.

## PostgreSQL configuration

Install PostgreSQL on Windows, create a database and least-privileged application user, then set:

```env
DATABASE_URL=postgresql+psycopg://sentinel:strong-password@localhost:5432/sentinel
```

Apply migrations:

```powershell
cd backend
.\.venv-win\Scripts\python.exe -m alembic upgrade head
cd ..
```

Use a managed secret store, encrypted backups, TLS database connections, and credential rotation in production.

## API overview

All application APIs are under `/api/v1`.

| Area | Important endpoints |
|---|---|
| Authentication | `/auth/register`, `/auth/register/verify-otp`, `/auth/login`, `/auth/otp-login/*`, `/auth/password/*`, `/auth/logout`, `/auth/me` |
| Dataset onboarding | `/datasets/status`, `/datasets/imports`, `/datasets/current` |
| Dashboard | `/dashboard/summary` |
| Business data | `/sales`, `/finance`, `/inventory`, `/support`, `/employees`, `/customers` |
| Analytics | `/analytics/overview`, `/analytics/products`, `/analytics/regions`, `/analytics/customers/lifetime-value`, `/analytics/summary` |
| Sentinel AI | `/ai/chat`, `/ai/conversations`, `/ai/forecast`, `/ai/anomalies`, `/ai/dataset-intelligence` |
| Files and reports | `/files`, `/files/uploads`, `/files/reports`, `/files/{id}/view`, `/files/{id}/download` |
| Governance | invitations, audit logs, and report schedules under `/governance` |

Swagger documents validation, pagination, filtering, sorting, and response schemas at <http://localhost:8000/docs>.

## Development commands

Start the backend with reload:

```powershell
cd backend
.\.venv-win\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Start the frontend separately:

```powershell
cd frontend
npm run dev
```

Apply migrations:

```powershell
cd backend
.\.venv-win\Scripts\python.exe -m alembic upgrade head
```

## Testing

Load `.env` into the current PowerShell process and run all Python tests:

```powershell
. .\scripts\windows\Import-SentinelEnv.ps1
Import-SentinelEnv -Path .\.env
backend\.venv-win\Scripts\python.exe -m pytest backend\tests agents\tests -q
```

Validate the frontend:

```powershell
cd frontend
npx tsc --noEmit
npm run build
```

Validate migrations against a disposable SQLite database by temporarily setting `DATABASE_URL` to a new file, applying `alembic upgrade head`, and deleting only that verified disposable file afterward.

The test suite covers authentication, OTP security, session revocation, fresh-session data clearing, cross-tenant access, role enforcement, uploads, imports, PDFs, analytics, Sentinel conversation, exact calculations, risks, sentiment, forecasting, anomalies, invitations, and scheduled reports.

## Synthetic data

Generate deterministic normalized CSV datasets:

```powershell
backend\.venv-win\Scripts\python.exe synthetic_data\seed.py
```

Generate and replace the local database seed data:

```powershell
backend\.venv-win\Scripts\python.exe synthetic_data\seed.py --database --reset
```

Never use `--reset` with a production database.

## Troubleshooting

### Site cannot be reached

```powershell
Get-Content .sentinel\backend-error.log -Tail 100
Get-Content .sentinel\frontend-error.log -Tail 100
.\scripts\windows\stop.ps1
.\scripts\windows\start.ps1 -SkipSetup
```

Check ports:

```powershell
Get-NetTCPConnection -LocalPort 3000,8000 -State Listen
```

### OTP email is not received

- Confirm SMTP variables exist in `.env`.
- For Gmail, use an App Password and enable two-step verification.
- Confirm `EMAIL_FROM` is authorized by the provider.
- Check spam and provider delivery logs.
- Never use the normal mailbox password as `SMTP_PASSWORD`.

### Database migration fails

```powershell
cd backend
.\.venv-win\Scripts\python.exe -m alembic current
.\.venv-win\Scripts\python.exe -m alembic heads
.\.venv-win\Scripts\python.exe -m alembic upgrade head
```

### Dashboard redirects to onboarding

This is expected for a new session. Upload a dataset before opening the dashboard.

## Additional documentation

- [Architecture](docs/architecture.md)
- [ER diagram](docs/er-diagram.md)
- [Windows runbook](docs/windows.md)
- [Data Agent](agents/README.md)
- [Database notes](database/README.md)
- [Synthetic data](synthetic_data/README.md)

## Production checklist

- Use PostgreSQL rather than SQLite.
- Terminate TLS at a trusted reverse proxy.
- Store secrets in a managed secret service.
- Configure SPF, DKIM, and DMARC for email.
- Run a durable background worker for large imports and scheduled reports.
- Configure backups, restore testing, monitoring, dependency scanning, and centralized logs.
- Host the selected open-source model on appropriately sized CPU/GPU infrastructure.
- Review retention requirements before changing the session-only data policy.

## License

No open-source license has been selected. Add an organization-approved license before external redistribution.
