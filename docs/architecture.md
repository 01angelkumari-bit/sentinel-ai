# Architecture

Backend requests pass through FastAPI routers into application services. Services enforce use cases and transact through SQLAlchemy repositories; ORM models remain isolated in the infrastructure layer. JWT identity is extracted by a reusable dependency, so authorization can be extended consistently.

The frontend stores no access token in browser storage. The login flow writes the access token to an `HttpOnly`, `Secure` (in production), `SameSite=Lax` cookie. Next.js middleware gates dashboard routes, while the dashboard validates the session with the API.

The supported local runtime is native Windows: SQLite for local persistence, FastAPI under a Python virtual environment, and Next.js under Node.js. PowerShell scripts manage setup, migrations, process lifecycle, and logs. PostgreSQL is selected for production by changing the SQLAlchemy `DATABASE_URL`.

## Production operating notes

Run `alembic upgrade head` as a deploy step, configure a strong unique JWT secret from a secret manager, terminate TLS at an ingress, restrict CORS to trusted origins, and add rate limiting/auditing at the edge.
