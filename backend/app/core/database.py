from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .config import settings

# ─── Sync engine (SQLite o PostgreSQL) ───────────────────────────────────────
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    connect_args=connect_args,
    **({"pool_size": 10, "max_overflow": 20} if not settings.DATABASE_URL.startswith("sqlite") else {}),
)

# Habilitar WAL y foreign keys en SQLite
if settings.DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(conn, _):
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ─── Async engine (opcional, solo si no es SQLite) ───────────────────────────
async_engine = None
AsyncSessionLocal = None

if not settings.DATABASE_URL.startswith("sqlite"):
    try:
        from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
        async_engine = create_async_engine(settings.DATABASE_URL_ASYNC, pool_pre_ping=True)
        AsyncSessionLocal = sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
    except Exception:
        pass

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_async_db():
    if AsyncSessionLocal:
        async with AsyncSessionLocal() as session:
            yield session
    else:
        # Fallback síncrono en SQLite
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()
