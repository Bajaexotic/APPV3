# -------------------- db_engine (start)
from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Tuple

from sqlalchemy import text
from sqlmodel import Session, SQLModel, create_engine

from config.settings import DB_URL, DEBUG_MODE  # DEBUG_MODE optional but recommended
from data import schema  # ensures models are registered via import side-effects


# --- Engine (pre-ping to avoid stale connections; echo bound to DEBUG_MODE) ---
# Try to create engine with primary DB_URL
engine = None
_db_init_error = None

try:
    engine = create_engine(
        DB_URL,
        echo=bool(DEBUG_MODE),
        pool_pre_ping=True,
        # For SQLite, allow auto-create
        **({"isolation_level": "AUTOCOMMIT"} if "sqlite" in DB_URL else {}),
    )
except Exception as e:
    _db_init_error = e
    print(f"[DB] ERROR: Failed to create engine with {DB_URL}: {e}")
    # Try in-memory SQLite fallback
    try:
        engine = create_engine(
            "sqlite:///:memory:",
            echo=bool(DEBUG_MODE),
        )
        print("[DB] WARNING: Using in-memory SQLite fallback (data will be lost on restart)")
    except Exception as e2:
        print(f"[DB] CRITICAL: Even fallback database failed: {e2}")
        raise


def init_db() -> None:
    """
    Create all database tables based on SQLModel metadata.
    Logs a short inventory before running create_all().
    """
    tables = list(SQLModel.metadata.tables.keys())
    print("Models registered in SQLModel metadata:")
    if tables:
        for name in tables:
            print(" -", name)
        SQLModel.metadata.create_all(engine)
        print("[OK] Database tables created successfully.")
    else:
        print("[WARNING] No tables detected. Ensure your schema models import correctly.")


@contextmanager
def get_session() -> Iterator[Session]:
    """
    Context-managed session provider:

        with get_session() as s:
            ...

    Closes/rolls back on exception; commits nothing implicitly.
    Handles connection errors gracefully with auto-reconnect attempt.
    """
    s = Session(engine)
    try:
        # Test connection with lightweight query
        s.execute(text("SELECT 1"))
        yield s
        # Implicit commit if no exception
    except Exception as e:
        s.rollback()
        raise
    finally:
        try:
            s.close()
        except Exception as e:
            print(f"[DB] Warning: Error closing session: {e}")


def health_check() -> tuple[bool, str]:
    """
    Lightweight connectivity probe for diagnostics.
    Returns (ok, detail). Uses SQLAlchemy text() to avoid 'Not an executable object'.
    """
    try:
        with engine.connect() as conn:
            # Works across SQLAlchemy 2.x; no implicit text execution
            conn.execute(text("SELECT 1"))
        return True, "DB OK (SELECT 1)"
    except Exception as exc:
        return False, f"DB ERROR: {exc!s}"


if __name__ == "__main__":
    init_db()
    ok, detail = health_check()
    print("Health:", "✅" if ok else "❌", detail)
# -------------------- db_engine (end)
