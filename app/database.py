import os
import sqlite3
from contextlib import contextmanager
from typing import Generator, Any, List, Dict, Optional
from app.config import (
    DATABASE_PATH,
    SCHEMA_PATH,
    DATABASE_URL,
    IS_POSTGRES,
    SUPABASE_SCHEMA_PATH,
)

# Optional psycopg2 import when connecting to Supabase / PostgreSQL
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    psycopg2 = None
    RealDictCursor = None


def _adapt_query(query: str) -> str:
    """Adapts query parameter placeholders between SQLite (?) and PostgreSQL (%s)."""
    if IS_POSTGRES:
        return query.replace("?", "%s")
    return query


class CursorProxy:
    """
    Transparent cursor wrapper that:
    1. Replaces ? with %s when running on PostgreSQL (Supabase).
    2. Automatically tracks lastrowid on PostgreSQL via RETURNING id if not present.
    """
    def __init__(self, real_cursor, is_postgres: bool):
        self._cursor = real_cursor
        self._is_postgres = is_postgres
        self.lastrowid = getattr(real_cursor, "lastrowid", None)

    def execute(self, query: str, params: tuple = None):
        if self._is_postgres:
            q_clean = query.strip()
            # If INSERT and no RETURNING clause, append RETURNING id to capture lastrowid
            if q_clean.upper().startswith("INSERT") and "RETURNING" not in q_clean.upper():
                q_clean += " RETURNING id"
                adapted = q_clean.replace("?", "%s")
                if params is not None:
                    res = self._cursor.execute(adapted, params)
                else:
                    res = self._cursor.execute(adapted)
                try:
                    row = self._cursor.fetchone()
                    if isinstance(row, dict):
                        self.lastrowid = row.get("id") or list(row.values())[0]
                    elif isinstance(row, (list, tuple)):
                        self.lastrowid = row[0]
                except Exception:
                    self.lastrowid = None
                return res
            else:
                adapted = q_clean.replace("?", "%s")
                if params is not None:
                    return self._cursor.execute(adapted, params)
                return self._cursor.execute(adapted)
        else:
            if params is not None:
                res = self._cursor.execute(query, params)
            else:
                res = self._cursor.execute(query)
            self.lastrowid = self._cursor.lastrowid
            return res

    def executemany(self, query: str, seq_of_params):
        if self._is_postgres:
            adapted = query.replace("?", "%s")
            return self._cursor.executemany(adapted, seq_of_params)
        return self._cursor.executemany(query, seq_of_params)

    def fetchone(self):
        return self._cursor.fetchone()

    def fetchall(self):
        return self._cursor.fetchall()

    def fetchmany(self, size=None):
        return self._cursor.fetchmany(size) if size else self._cursor.fetchmany()

    @property
    def rowcount(self):
        return self._cursor.rowcount

    def close(self):
        return self._cursor.close()

    def __getattr__(self, name):
        return getattr(self._cursor, name)

    def __iter__(self):
        return iter(self._cursor)


class ConnectionProxy:
    """Connection wrapper ensuring cursors use CursorProxy."""
    def __init__(self, real_conn, is_postgres: bool):
        self._conn = real_conn
        self._is_postgres = is_postgres

    def cursor(self):
        real_cur = self._conn.cursor()
        return CursorProxy(real_cur, self._is_postgres)

    def commit(self):
        return self._conn.commit()

    def rollback(self):
        return self._conn.rollback()

    def close(self):
        return self._conn.close()

    def executescript(self, sql_script: str):
        if hasattr(self._conn, "executescript"):
            return self._conn.executescript(sql_script)
        else:
            with self.cursor() as cur:
                return cur.execute(sql_script)

    def __getattr__(self, name):
        return getattr(self._conn, name)


def get_connection():
    """Create a new database connection (Supabase PostgreSQL or SQLite)."""
    if IS_POSTGRES:
        if psycopg2 is None:
            raise RuntimeError(
                "psycopg2 is required for Supabase / PostgreSQL. Run: pip install psycopg2-binary"
            )
        real_conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        real_conn.autocommit = False
        return ConnectionProxy(real_conn, is_postgres=True)
    else:
        real_conn = sqlite3.connect(DATABASE_PATH, timeout=15.0)
        real_conn.execute("PRAGMA foreign_keys = ON;")
        real_conn.row_factory = sqlite3.Row
        return ConnectionProxy(real_conn, is_postgres=False)


@contextmanager
def get_db_context() -> Generator[Any, None, None]:
    """Context manager for database operations."""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_db():
    """FastAPI Dependency for database access."""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Initialize database tables, views, and indexes."""
    if IS_POSTGRES:
        schema_file = SUPABASE_SCHEMA_PATH if SUPABASE_SCHEMA_PATH.exists() else SCHEMA_PATH
        with open(schema_file, "r", encoding="utf-8") as f:
            schema_sql = f.read()

        with get_db_context() as conn:
            cur = conn.cursor()
            cur.execute(schema_sql)
        print("Supabase PostgreSQL database initialized successfully.")
    else:
        if not os.path.exists(SCHEMA_PATH):
            raise FileNotFoundError(f"Schema file not found at {SCHEMA_PATH}")

        with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
            schema_sql = f.read()

        conn = get_connection()
        try:
            conn.executescript(schema_sql)
            conn.commit()
            print("Database initialized successfully with schema.sql.")
        finally:
            conn.close()


def fetch_one(query: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
    """Execute query and fetch a single record as a dictionary."""
    with get_db_context() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        row = cursor.fetchone()
        return dict(row) if row else None


def fetch_all(query: str, params: tuple = ()) -> List[Dict[str, Any]]:
    """Execute query and fetch all records as a list of dictionaries."""
    with get_db_context() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def execute_insert(query: str, params: tuple = ()) -> int:
    """Execute INSERT query and return the new row id."""
    with get_db_context() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        return cursor.lastrowid or 0


def execute_modify(query: str, params: tuple = ()) -> int:
    """Execute UPDATE or DELETE query and return affected row count."""
    with get_db_context() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        return cursor.rowcount
