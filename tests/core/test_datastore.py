from dataclasses import dataclass, field
from datetime import datetime
from typing import cast

from ksmonitor.core import datastore as datastore_module
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
    def test_register_creates_table_and_columns(self, tmp_path):
        store = DataStore(tmp_path / "store.db")
        store.register("dummy", DummySchema)
        cols, rows = store.read("dummy")
        assert cols == ["polled_at", "alpha", "beta"]
        assert rows == []

    def test_update_buffers_then_save_flushes(self, tmp_path):
        store = DataStore(tmp_path / "store.db")
        store.register("dummy", DummySchema)
        store.update(
            "dummy",
            dummy_output([{"alpha": "1", "beta": "x"}, {"alpha": "2", "beta": "y"}]),
        )

        # Not yet flushed → table is empty on disk
        _, rows = store.read("dummy")
        assert rows == []

        store.save("dummy")
        _, rows = store.read("dummy")
        assert rows == [
            ("2026-01-01T00:00:00", 1, "x"),
            ("2026-01-01T00:00:00", 2, "y"),
        ]

    def test_save_and_reopen_round_trip(self, tmp_path):
        # Long retention so DummyOutput's pinned 2026-01-01 polled_at survives.
        path = tmp_path / "store.db"
        store = DataStore(path, retention_days=365 * 100)
        store.register("dummy", DummySchema)
        store.update(
            "dummy",
            dummy_output([{"alpha": "1", "beta": "x"}, {"alpha": "2", "beta": "y"}]),
        )
        store.save()
        store.close()

        reopened = DataStore(path, retention_days=365 * 100)
        cols, rows = reopened.read("dummy")
        assert cols == ["polled_at", "alpha", "beta"]
        assert len(rows) == 2

    def test_incremental_save(self, tmp_path):
        path = tmp_path / "store.db"
        store = DataStore(path, retention_days=365 * 100)
        store.register("dummy", DummySchema)

        store.update("dummy", dummy_output([{"alpha": "1", "beta": "a"}]))
        store.save()

        store.update("dummy", dummy_output([{"alpha": "2", "beta": "b"}]))
        store.save()

        _, rows = store.read("dummy")
        assert len(rows) == 2
        assert rows[1] == ("2026-01-01T00:00:00", 2, "b")


class TestDataStoreRetentionAndRace:
    def test_retention_sweep_on_init(self, tmp_path, monkeypatch):
        path = tmp_path / "store.db"

        # First open: write a row whose polled_at is 2026-01-01
        store = DataStore(path)
        store.register("dummy", DummySchema)
        store.update("dummy", dummy_output([{"alpha": "1", "beta": "old"}]))
        store.save()
        store.close()

        # Pin "now" to 14 days after the row's polled_at so the default
        # 7-day retention sweeps it on reopen.
        class _FixedDatetime(datetime):
            @classmethod
            def now(cls, tz=None):
                return datetime(2026, 1, 15)

        monkeypatch.setattr(datastore_module, "datetime", _FixedDatetime)

        reopened = DataStore(path)
        _, rows = reopened.read("dummy")
        assert rows == []

    def test_retention_keeps_recent_rows(self, tmp_path):
        path = tmp_path / "store.db"
        store = DataStore(path, retention_days=365)
        store.register("dummy", DummySchema)
        store.update("dummy", dummy_output([{"alpha": "1", "beta": "fresh"}]))
        store.save()
        store.close()

        reopened = DataStore(path, retention_days=365)
        _, rows = reopened.read("dummy")
        assert len(rows) == 1

    def test_unregister_does_not_drop_table(self, tmp_path):
        path = tmp_path / "store.db"
        store = DataStore(path, retention_days=365)
        store.register("dummy", DummySchema)
        store.update("dummy", dummy_output([{"alpha": "1", "beta": "keep"}]))
        store.save()
        store.unregister("dummy")
        store.close()

        reopened = DataStore(path, retention_days=365)
        _, rows = reopened.read("dummy")
        assert len(rows) == 1

    def test_unregister_flushes_pending_buffer(self, tmp_path):
        path = tmp_path / "store.db"
        store = DataStore(path)
        store.register("dummy", DummySchema)
        store.update("dummy", dummy_output([{"alpha": "1", "beta": "x"}]))
        # Note: no explicit save() before unregister.
        store.unregister("dummy")

        _, rows = store.read("dummy")
        assert len(rows) == 1

    def test_update_after_unregister_logs_warning(self, tmp_path, caplog):
        store = DataStore(tmp_path / "store.db")
        store.register("dummy", DummySchema)
        store.unregister("dummy")
        with caplog.at_level("WARNING"):
            store.update("dummy", dummy_output([{"alpha": "1", "beta": "x"}]))
        assert any("unregistered" in r.message for r in caplog.records)
