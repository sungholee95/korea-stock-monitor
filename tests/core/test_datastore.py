from dataclasses import dataclass, field
from datetime import datetime
from typing import cast

from ksmonitor.core.datastore import DataStore
from ksmonitor.core.protocols import RestResponseOutput


@dataclass
class DummyOutput:
    """Minimal output for testing DataStore without dependencies on real endpoints."""

    output_raw: list[dict[str, str]]
    polled_at: datetime = field(
        default_factory=lambda: datetime(2026, 1, 1), init=False
    )
    alpha: list[int] = field(default_factory=list, init=False, metadata={"ko": "Alpha"})
    beta: list[str] = field(default_factory=list, init=False, metadata={"ko": "Beta"})

    def __post_init__(self) -> None:
        for row in self.output_raw:
            self.alpha.append(int(row["alpha"]))
            self.beta.append(str(row["beta"]))


DummySchema = cast(type[RestResponseOutput], DummyOutput)


def dummy_output(rows: list[dict[str, str]]) -> RestResponseOutput:
    return cast(RestResponseOutput, DummyOutput(rows))


class TestDataStoreRoundTrip:
    def test_from_endpoint_columns(self):
        store = DataStore.from_endpoint("dummy", DummySchema)
        assert store.columns == ["polled_at", "alpha", "beta"]
        assert store.rows == []

    def test_update_appends_rows(self):
        store = DataStore.from_endpoint("dummy", DummySchema)
        store.update(
            dummy_output([{"alpha": "1", "beta": "x"}, {"alpha": "2", "beta": "y"}])
        )

        assert len(store.rows) == 2
        assert store.rows == [
            ("2026-01-01T00:00:00", 1, "x"),
            ("2026-01-01T00:00:00", 2, "y"),
        ]

    def test_save_and_load_round_trip(self, tmp_path):
        store = DataStore.from_endpoint("dummy", DummySchema)
        store.update(
            dummy_output([{"alpha": "1", "beta": "x"}, {"alpha": "2", "beta": "y"}])
        )

        db_path = tmp_path / "store.db"
        store.save_to_disk(db_path)

        loaded = DataStore.from_disk(db_path, "dummy")
        assert loaded.columns == store.columns
        assert loaded.rows == store.rows

    def test_incremental_save(self, tmp_path):
        """Only new rows since last save are written."""
        store = DataStore.from_endpoint("dummy", DummySchema)
        db_path = tmp_path / "store.db"

        # First batch
        store.update(dummy_output([{"alpha": "1", "beta": "a"}]))
        store.save_to_disk(db_path)

        # Second batch
        store.update(dummy_output([{"alpha": "2", "beta": "b"}]))
        store.save_to_disk(db_path)

        loaded = DataStore.from_disk(db_path, "dummy")
        assert len(loaded.rows) == 2
        assert loaded.rows[1] == ("2026-01-01T00:00:00", 2, "b")
