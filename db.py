"""
Centralized database connection management.

All database access in MealMCP goes through a :class:`Database` instance, which
owns connection lifecycle:

* PostgreSQL connections are drawn from a process-wide pool
  (:class:`psycopg2.pool.ThreadedConnectionPool`) and returned after use, instead
  of opening a fresh TCP+TLS connection per query and relying on the garbage
  collector to close it.
* SQLite connections are opened per use and explicitly closed.

Usage::

    db = get_database("postgresql", "postgresql://...")
    with db.connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT 1")

The ``with db.connection()`` block commits on success and rolls back on error,
matching the previous ``with psycopg2.connect(...) as conn`` semantics, then
releases the connection back to the pool.
"""

from __future__ import annotations

import logging
import os
import sqlite3
import threading
from contextlib import contextmanager
from typing import Dict, Iterator, Optional, Tuple
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

_POSTGRES_PREFIXES = ("postgresql://", "postgres://")


def is_postgres_url(connection_string: Optional[str]) -> bool:
    """Return True if the connection string looks like a PostgreSQL URL."""
    return bool(connection_string) and connection_string.startswith(_POSTGRES_PREFIXES)


def normalize_backend(backend: Optional[str], connection_string: Optional[str]) -> str:
    """Resolve the effective backend name from an explicit value and/or URL."""
    if backend:
        backend = backend.lower()
        if backend in ("postgres", "postgresql"):
            return "postgresql"
        if backend == "sqlite":
            return "sqlite"
    return "postgresql" if is_postgres_url(connection_string) else "sqlite"


class Database:
    """Owns connection lifecycle for a single database (pooled for PostgreSQL)."""

    def __init__(
        self,
        backend: str,
        connection_string: str,
        *,
        minconn: int = 1,
        maxconn: Optional[int] = None,
    ):
        self.backend = normalize_backend(backend, connection_string)
        self.connection_string = connection_string
        self._pool = None
        self._lock = threading.Lock()

        if self.backend == "postgresql":
            if maxconn is None:
                maxconn = int(os.getenv("PANTRY_DB_POOL_SIZE", "10"))
            self._minconn = max(1, minconn)
            self._maxconn = max(self._minconn, maxconn)
            self._pg_kwargs = self._parse_pg_url(connection_string)

    @staticmethod
    def _parse_pg_url(connection_string: str) -> Dict[str, object]:
        parsed = urlparse(connection_string)
        return {
            "host": parsed.hostname,
            "port": parsed.port or 5432,
            "dbname": parsed.path.lstrip("/"),
            "user": parsed.username,
            "password": parsed.password,
        }

    def _ensure_pool(self):
        if self._pool is not None:
            return self._pool
        with self._lock:
            if self._pool is None:
                from psycopg2.pool import ThreadedConnectionPool

                logger.info(
                    "Creating PostgreSQL connection pool (min=%d, max=%d) for %s",
                    self._minconn,
                    self._maxconn,
                    self._pg_kwargs.get("host"),
                )
                self._pool = ThreadedConnectionPool(
                    self._minconn, self._maxconn, **self._pg_kwargs
                )
        return self._pool

    @contextmanager
    def connection(self) -> Iterator[object]:
        """Yield a DB-API connection, committing on success / rolling back on error."""
        if self.backend == "postgresql":
            pool = self._ensure_pool()
            conn = pool.getconn()
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                pool.putconn(conn)
        else:
            conn = sqlite3.connect(self.connection_string)
            conn.isolation_level = None  # autocommit, matches historical behavior
            try:
                yield conn
            finally:
                conn.close()

    def closeall(self) -> None:
        """Close every pooled connection (call on shutdown)."""
        if self._pool is not None:
            self._pool.closeall()
            self._pool = None


_databases: Dict[Tuple[str, str], Database] = {}
_databases_lock = threading.Lock()


def get_database(backend: Optional[str], connection_string: str, **kwargs) -> Database:
    """Return a shared :class:`Database` for this backend/connection string.

    Instances are cached per (backend, connection_string) so that a single
    connection pool is reused across the many short-lived manager objects the
    web and MCP layers create per request.
    """
    resolved = normalize_backend(backend, connection_string)
    key = (resolved, connection_string)
    db = _databases.get(key)
    if db is None:
        with _databases_lock:
            db = _databases.get(key)
            if db is None:
                db = Database(resolved, connection_string, **kwargs)
                _databases[key] = db
    return db


def close_all_databases() -> None:
    """Dispose of every cached database (test teardown / process shutdown)."""
    with _databases_lock:
        for db in _databases.values():
            db.closeall()
        _databases.clear()
