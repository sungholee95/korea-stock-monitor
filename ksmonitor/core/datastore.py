from __future__ import annotations

import logging
import sqlite3
from dataclasses import fields
from pathlib import Path
from typing import TYPE_CHECKING

import polars as pl

if TYPE_CHECKING:
    from ..adapters.kis.endpoints import RestResponse, RestResponseOutput

logger = logging.getLogger(__name__)


class DataStore:
    def __init__(self, name: str) -> None:
        self.name = name
        self._ko_fields: list = []
        self._columns: list[str] = []
        self._rows: list[tuple] = []
        self._rows_saved: int = 0

    @classmethod
    def from_endpoint(cls, name: str, endpoint_schema: type[RestResponseOutput]):
        new_store = cls(name)
        new_store._ko_fields = [
            f for f in fields(endpoint_schema) if f.metadata.get("ko")
        ]
        new_store._columns = ["polled_at", *(f.name for f in new_store._ko_fields)]
        new_store._rows = []
        return new_store

    def update(self, new_response: RestResponse) -> None:
        output = new_response.output
        polled_at = output.polled_at.isoformat()

        if isinstance(output.output_raw, dict):
            self._rows.append(
                (polled_at, *(getattr(output, f.name) for f in self._ko_fields))
            )
        else:
            for values in zip(*(getattr(output, f.name) for f in self._ko_fields)):
                self._rows.append((polled_at, *values))

    def to_polars(self):
        return pl.DataFrame(self._rows, schema=self._columns, orient="row")

    def save_to_disk(self, path: Path) -> None:
        col_defs = ", ".join(f'"{c}" TEXT' for c in self._columns)
        placeholders = ", ".join("?" * len(self._columns))
        rows_to_save = self._rows[self._rows_saved :]

        with sqlite3.connect(path) as conn:
            conn.execute(f'CREATE TABLE IF NOT EXISTS "{self.name}" ({col_defs})')
            conn.executemany(
                f'INSERT INTO "{self.name}" VALUES ({placeholders})', rows_to_save
            )
            self._rows_saved += len(rows_to_save)

        logger.debug(f"Saved `{self.name}` ({len(rows_to_save)} rows) to `{path}`")

    @classmethod
    def from_disk(cls, path: Path, name: str) -> DataStore:
        store = cls(name)

        with sqlite3.connect(path) as conn:
            cursor = conn.execute(f'SELECT * FROM "{name}"')
            store._columns = [desc[0] for desc in cursor.description]
            store._rows = list(cursor.fetchall())
            store._rows_saved = len(store._rows)

        return store
