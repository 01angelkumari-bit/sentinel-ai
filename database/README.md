# Database

SQLite is the native Windows development database and PostgreSQL is the supported production system of record. Both are accessed through SQLAlchemy. Alembic migrations live in `backend/alembic`; never modify production schemas outside a reviewed migration.

The normalized business schema covers customer, product, sales, inventory, finance, workforce, support, supplier, and report domains. See `docs/er-diagram.md` for relationships and `synthetic_data/csv` for deterministic reference data.
