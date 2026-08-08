# Architecture

```mermaid
flowchart TB
    data["Organization CSV / Excel data"] --> db["Neon PostgreSQL"]
    db --> api["FastAPI API on Render"]
    api --> collector["Data Collection Agent"]
    collector --> sales["Sales Agent"]
    collector --> finance["Finance Agent"]
    collector --> hr["HR Agent"]
    collector --> support["Support Agent"]
    collector --> inventory["Inventory Agent"]
    sales --> risk["Risk Analysis Agent"]
    finance --> risk
    hr --> risk
    support --> risk
    inventory --> risk
    risk --> recommendation["Recommendation Agent"]
    recommendation --> executive["Executive Summary Agent"]
    executive --> dashboard["Sentinel AI Dashboard on Vercel"]
    dashboard --> outputs["Forecasting, CSV exports, and PDF reports"]
```

Every request is scoped by the authenticated organization. The API resolves the
JWT to a revocable server-side session and current user, then tenant-filtered
repositories enforce `organization_id` before any data, file, report, or AI
conversation is read or written.

```mermaid
sequenceDiagram
    participant U as User
    participant N as Next.js / Vercel
    participant F as FastAPI / Render
    participant P as Neon PostgreSQL
    participant D as Persistent Disk

    U->>N: Sign in or verify OTP
    N->>F: Authenticate
    F->>P: Validate user, organization, and session
    F-->>N: JWT
    N-->>U: HttpOnly session cookie
    U->>N: Upload dataset
    N->>F: Authorized file stream
    F->>D: Save unique source file
    F->>P: Batch insert tenant-tagged records
    U->>N: Open dashboard or ask Sentinel
    N->>F: Authorized analytics request
    F->>P: Tenant-filtered calculations
    F-->>N: Exact metrics and evidence
```

The frontend never stores access tokens in browser storage. Next.js writes the
token to an `HttpOnly`, `Secure` in production, `SameSite=Lax` cookie. Server-side
route handlers relay authorized calls to FastAPI, and middleware gates protected
routes.

Local development is native Windows with SQLite, FastAPI, and Next.js. Production
uses Vercel, Render, Neon PostgreSQL, and a Render persistent disk. Alembic runs as
a pre-deploy command before the new API revision starts.
