# Authentication performance

Sentinel authentication performs only identity work on the critical path:

1. Load the indexed user and organization row.
2. Verify the password with Argon2id.
3. create and persist a revocable JWT session.
4. Return minimal user, organization, and role metadata.
5. Create the secure browser cookie and navigate to dataset selection.

Dashboard analytics, file parsing, AI workflows, reports, and PDFs are not executed by login or registration. The dashboard shell streams before its analytics summary, and CSV/XLSX imports are queued for background processing.

## Operational endpoints

- `GET /health` checks only that the API process is responsive.
- `GET /ready` verifies that the API can query PostgreSQL.

Successful login responses expose a `Server-Timing` header with database, password verification, session/JWT, commit, and total durations. Backend logs include a request ID and `AUTH_REQUEST_START` / `AUTH_REQUEST_END` events. Requests slower than `AUTH_SLOW_REQUEST_MS` are logged as warnings.

## Database pool settings

```env
DATABASE_POOL_SIZE=5
DATABASE_MAX_OVERFLOW=5
DATABASE_POOL_TIMEOUT_SECONDS=5
DATABASE_POOL_RECYCLE_SECONDS=300
DATABASE_CONNECT_TIMEOUT_SECONDS=5
AUTH_SLOW_REQUEST_MS=1000
```

Use a pooled Neon PostgreSQL connection string in production. Cache and analytics keys must continue to include `organization_id`.

## Verification

From the repository root on Windows:

```powershell
$env:PYTHONPATH = "backend"
.\backend\.venv-win\Scripts\python.exe -m pytest backend\tests -q
Set-Location frontend
npm run build
```

Do not use large synthetic registration runs against real email infrastructure. Load-test password login with dedicated test users and a non-production database.
