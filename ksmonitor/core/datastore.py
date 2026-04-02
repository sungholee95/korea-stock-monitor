from __future__ import annotations

import logging
import sqlite3
from dataclasses import fields
from pathlib import Path

import polars as pl

from .protocols import RestResponseOutput

logger = logging.getLogger(__name__)


TYPE_MAPPER = {
    int: "INTEGER",
    float: "REAL",
    str: "TEXT",
    bool: "INTEGER",  # SQLite does not have a separate Boolean storage class
}


class DataStore:
    def __init__(self, name: str) -> None:
        self.name = name
        self._ko_fields: list = []
        self.columns: list[str] = []
        self.rows: list[tuple] = []
        self._rows_saved: int = 0

        self._col_defs = ""
        self._placeholders = ""

    @classmethod
    def from_endpoint(
        cls, name: str, endpoint_schema: type[RestResponseOutput]
    ) -> DataStore:
        new_store = cls(name)
        new_store._ko_fields = [
            f for f in fields(endpoint_schema) if f.metadata.get("ko")
        ]

        new_store.columns = ["polled_at", *(f.name for f in new_store._ko_fields)]
        new_store._placeholders = ", ".join("?" * len(new_store.columns))
        new_store._col_defs = "polled_at TEXT,"  # for "polled_at" column
        new_store._col_defs += ", ".join(
            [
                # list[str].__args__[0] returns str == the inner type
                f"{f.name} {TYPE_MAPPER[f.type.__args__[0]]}"
                for f in new_store._ko_fields
            ]
        )  # add data types of other columns

        new_store.rows = []
        return new_store

    def update(self, new_output: RestResponseOutput) -> None:
        output = new_output
        polled_at = output.polled_at.isoformat()

        if isinstance(output.output_raw, dict):
            self.rows.append(
                (polled_at, *(getattr(output, f.name) for f in self._ko_fields))
            )
        else:
            for values in zip(*(getattr(output, f.name) for f in self._ko_fields)):
                self.rows.append((polled_at, *values))

    def to_polars(self):
        return pl.DataFrame(self.rows, schema=self.columns, orient="row")

    def save_to_disk(self, path: Path) -> None:
        rows_to_save = self.rows[self._rows_saved :]
        with sqlite3.connect(path) as conn:
            conn.execute(f'CREATE TABLE IF NOT EXISTS "{self.name}" ({self._col_defs})')
            conn.executemany(
                f'INSERT INTO "{self.name}" VALUES ({self._placeholders})', rows_to_save
            )
            self._rows_saved += len(rows_to_save)

        logger.debug(f"Saved `{self.name}` ({len(rows_to_save)} rows) to `{path}`")

    @classmethod
    def from_disk(cls, path: Path, name: str) -> DataStore:
        store = cls(name)

        with sqlite3.connect(path) as conn:
            cursor = conn.execute(f'SELECT * FROM "{name}"')
            store.columns = [desc[0] for desc in cursor.description]
            store.rows = list(cursor.fetchall())
            store._rows_saved = len(store.rows)

        return store
