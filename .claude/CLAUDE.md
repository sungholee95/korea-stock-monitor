# CLAUDE.md

## Commands

```bash
uv sync                                                             # install dependencies
uv run pytest tests                                                 # run all tests
uv run pytest tests/kiwoom/test_client.py                           # single test file
uv run pytest tests/kiwoom/test_client.py::TestClass::test_name     # single test
uv run ruff check . && uv run ruff format .                         # lint
```

Entry points for manual testing: `run_kiwoom.py` / `run_kis.py`. `scratches/` contains throwaway experiments.

## Project Overview

Korean stock monitoring/alerting app: polls **Kiwoom** and **KIS** REST APIs, stores data in `DataStore`, fires `BaseAlert` subclasses via Telegram when conditions are met. **Primary focus: Kiwoom adapter. KIS development paused.**

## Architecture

```
adapters/kis/      — KIS: auth, endpoints, REST/WS client (paused)
adapters/kiwoom/   — Kiwoom: auth, endpoints, REST client (active)
adapters/telegram/ — Telegram notifications (stub)
core/              — Broker-agnostic: DataStore, alerts, protocols
```

**Data flow:** `Endpoint` enum -> `REQUEST_REGISTRY` -> Request (builds headers/params with auth) -> `Subscription` (executes) -> Response (typed output) -> `DataStore` (SQLite + Polars)

`adapters/_base/` provides shared `Config`, `Auth`, and `Endpoint` ABCs — `core/` depends only on these, never on KIS/Kiwoom types directly. `RestRequest`/`RestResponse` in `core/client.py` are union type aliases.

### Endpoint registration

Each broker has `KISEndpoint` / `KiwoomEndpoint` enums (value = routing ID). Adding an endpoint:
1. Add enum member in `endpoints/_common.py`
2. Create module with `*Request`, `*Response`, `*ResponseOutput` dataclasses — `BaseRestRequest.__init_subclass__` auto-registers into `REQUEST_REGISTRY`; `*ResponseOutput` fields are `field(init=False, metadata={"ko": ...})` and populated by `__post_init__` parsing `output_raw`
3. Import in `endpoints/__init__.py`

KIS routes via `tr_id`; Kiwoom via `api_id`. Kiwoom `*Response` must also set `_output_key` ClassVar (e.g., `"trde_prica_upper"`); KIS always uses `"output"`. The `{"ko": "한글명"}` metadata drives both schema drift detection and `DataStore` column naming.

### DataStore

Keyed by subscription name. `from_endpoint(name, schema)` infers columns from `metadata={"ko": ...}` fields. `update()` appends rows; `save_to_disk()` incrementally writes new rows to SQLite; `to_polars()` returns a Polars DataFrame.

### Alert system

`BaseAlert` subclasses implement `evaluate(datastores) -> bool` and `format_message(datastores) -> str`. Base `check()` enforces cooldown before calling `evaluate`. Reference subscription via `subscription_name`.

### Auth & credentials

Secrets in Windows Credential Manager via `keyring`. Config YAMLs at `~/.ksmonitor/config/{kis,kiwoom}.yaml` hold only non-secret identifiers. API base URLs are hardcoded in config dataclasses — not YAML — to prevent hijacking.

### Rate limits

- Production: ≤ 20 REST calls/s; Paper (모의): ≤ 2 REST calls/s
- `_enforce_rate_limit()` checks `n_subscriptions / poll_rate` at start of `poll()`

### Not yet implemented

- WebSocket clients (stubs raise `NotImplementedError`)
- Telegram notification dispatch
- Pagination auto-fetch (`has_next_page()` exists; auto-fetch raises `NotImplementedError`)
- `monitor.py` orchestrator tying REST + WS + alerts + Telegram together

## Code Style

- **Python 3.12+**: `X | Y` unions, `match`, `kw_only` dataclasses, `from __future__ import annotations`
- **Ruff** for linting (`pyproject.toml`)
- Korean for domain descriptions and enum metadata; English for all code identifiers
- Private attributes: `_` prefix, initialized in `__init__`; `TYPE_CHECKING` guard for circular imports
- Booleans: `is_`/`has_`/`can_` prefix
- Type hints: `str | None` not `Optional[str]`; no string-quoted type hints
- Backticks in log/exception/docstring strings (e.g., `` `KISAuth.get_rest_headers()` ``)

## General Instructions

- Keep relevant existing comments when modifying code
- Suggest style improvements (renaming, etc.), but ONLY when appropriate
- For large changes (new modules, breaking changes), consult `.claude/architecture.md` for full project structure, KIS/Kiwoom adapter differences, and design decisions
