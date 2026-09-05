from collections.abc import Generator
from pathlib import Path
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from app.core.config import get_settings

database_url = get_settings().database_url
if database_url.startswith("postgresql://"):
    database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)
if database_url == "sqlite:///./sentinel.db":
    database_url = f"sqlite:///{(Path(__file__).resolve().parents[2] / 'sentinel.db').as_posix()}"
settings = get_settings()
engine_options: dict[str, object] = {
    "pool_pre_ping": True,
    "pool_recycle": settings.database_pool_recycle_seconds,
}
if database_url.startswith("sqlite"):
    engine_options.update({
        "connect_args": {"check_same_thread": False, "timeout": settings.database_connect_timeout_seconds},
    })
else:
    engine_options.update({
        "pool_size": settings.database_pool_size,
        "max_overflow": settings.database_max_overflow,
        "pool_timeout": settings.database_pool_timeout_seconds,
        "pool_use_lifo": True,
        "connect_args": {
            "connect_timeout": settings.database_connect_timeout_seconds,
            "application_name": "sentinel-api",
        },
    })
engine = create_engine(database_url, **engine_options)
if database_url.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def configure_sqlite(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute(f"PRAGMA busy_timeout={settings.database_connect_timeout_seconds * 1000}")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
class Base(DeclarativeBase): pass
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try: yield db
    finally: db.close()
