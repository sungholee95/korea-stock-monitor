from __future__ import annotations

import logging
import sqlite3
import threading
from dataclasses import Field, fields
from datetime import datetime, timedelta
from pathlib import Path

from .protocols import RestResponseOutput

logger = logging.getLogger(__name__)


TYPE_MAPPER = {
    int: "INTEGER",
    float: "REAL",
    str: "TEXT",
    bool: "INTEGER",  # SQLite does not have a separate Boolean storage class
}


class DataStore:
    """SQLite-backed store for polled subscription outputs.

    One DataStore per client, which owns one SQLite file with one table per
    subscription. Tables are addressed by subscription name. Rows are buffered
    in memory and flushed on `save()`. On init, a retention sweep deletes
    rows older than `retention_days` from every table in the file.

    `register()` must be called before `update()` for a given name. After
    `unregister()`, subsequent `update()` calls for that name are logged
    no-ops — this is the intended race-safe behavior for callers that may
    poll a subscription concurrently with unsubscribing it.
    """

    def __init__(
        self,
        path: Path,
        retention_days: int = 7,
    ) -> None:
        self.path = path
        self.retention_time = timedelta(days=retention_days)
        self.path.parent.mkdir(parents=True, exist_ok=True)

        # Single long-lived connection. `check_same_thread=False` plus the
        # lock allows sharing across the asyncio loop and any executor threads.
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        # Write-ahead log (WAL) mode allows concurrent read and write
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._lock = threading.Lock()

        self._ko_fields: dict[str, list[Field]] = {}
        self._placeholders: dict[str, str] = {}
        self._buffers: dict[str, list[tuple]] = {}

        self._sweep_retention()

    def _sweep_retention(self) -> None:
        cutoff = (datetime.now() - self.retention_time).isoformat()
        with self._lock:
            tables = [
                row[0]
                for row in self._conn.execute(
                    "SELECT name FROM sqlite_master "
                    "WHERE type='table' AND name NOT LIKE 'sqlite_%'"
                )
            ]

            n_rows_deleted = 0
            for table in tables:
                cur = self._conn.execute(
                    f'DELETE FROM "{table}" WHERE polled_at < ?', (cutoff,)
                )
                n_rows_deleted += cur.rowcount

            self._conn.commit()

        logger.info(
            f"Retention sweep: deleted {n_rows_deleted} row(s) older than {cutoff} "
            f"across {len(tables)} table(s)"
        )

    def register(self, name: str, schema: type[RestResponseOutput]) -> None:
        if name in self._ko_fields:
            logger.debug(f"`{name}` already registered; skipping")
            return

        ko_fields = [f for f in fields(schema) if f.metadata.get("ko")]
        placeholders = ", ".join("?" * (1 + len(ko_fields)))

        col_defs = "polled_at TEXT, "
        col_defs += ", ".join(
            # list[str].__args__[0] returns str (the "inner" type)
            # Plain types (int, str, ...) have no __args__ attribute
            f"{f.name} {TYPE_MAPPER[f.type.__args__[0] if hasattr(f.type, '__args__') else f.type]}"  # type: ignore[attr-defined]
            for f in ko_fields
        )

        with self._lock:
            self._conn.execute(f'CREATE TABLE IF NOT EXISTS "{name}" ({col_defs})')
            self._conn.commit()

        self._ko_fields[name] = ko_fields
        self._placeholders[name] = placeholders
        self._buffers[name] = []
        logger.debug(f"Registered `{name}`")

    def update(self, name: str, output: RestResponseOutput) -> None:
        # Both lookups via `.get()` so a concurrent `unregister()` between them
        # cannot raise KeyError. If `unregister()` deletes the dict entry after
        # this point, rows land on an orphaned list — a silent no-op, matching
        # the docstring's race-safety contract.
        ko_fields = self._ko_fields.get(name)
        buffer = self._buffers.get(name)
        if ko_fields is None or buffer is None:
            logger.warning(f"`update()` called for unregistered subscription `{name}`")
            return

        polled_at = output.polled_at.isoformat()
        if isinstance(output.output_raw, dict):
            buffer.append((polled_at, *(getattr(output, f.name) for f in ko_fields)))
        else:
            for values in zip(*(getattr(output, f.name) for f in ko_fields)):
                buffer.append((polled_at, *values))

    def save(self, name: str | None = None) -> None:
        names = [name] if name is not None else list(self._buffers)
        with self._lock:
            flushed: list[str] = []
            for n in names:
                rows = self._buffers.get(n)
                if not rows:
                    continue

                self._conn.executemany(
                    f'INSERT INTO "{n}" VALUES ({self._placeholders[n]})', rows
                )
                logger.debug(f"Saved `{n}` ({len(rows)} row(s)) to `{self.path}`")
                flushed.append(n)

            self._conn.commit()
            # Clear buffers only after commit succeeds, so a failed commit
            # leaves the in-memory rows intact for the next `save()`.
            for n in flushed:
                self._buffers[n] = []

    def unregister(self, name: str) -> None:
        if name not in self._ko_fields:
            logger.debug(f"`{name}` not registered; nothing to unregister")
            return

        self.save(name)
        del self._ko_fields[name]
        del self._placeholders[name]
        del self._buffers[name]
        logger.debug(f"Unregistered `{name}` (table preserved)")

    def read(self, name: str) -> tuple[list[str], list[tuple]]:
        with self._lock:
            cursor = self._conn.execute(f'SELECT * FROM "{name}"')
            columns = [desc[0] for desc in cursor.description]
            rows = list(cursor.fetchall())

        return columns, rows

    def close(self) -> None:
        self.save()
        with self._lock:
            self._conn.close()
