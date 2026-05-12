# CLAUDE.md

> Code style and conventions. For architecture and current state of the repo, see [.claude/architecture.md](.claude/architecture.md). 

## Commands

```bash
uv sync                                                             # install dependencies
uv run pytest tests                                                 # run all tests
uv run pytest tests/kiwoom/test_client.py                           # single test file
uv run pytest tests/kiwoom/test_client.py::TestClass::test_name     # single test
uv run ruff check . && uv run ruff format .                         # lint
```

Entry points: [main.py](main.py) is the orchestrator (REST poll + alert dispatch + Telegram bot via `asyncio.gather`).

## Project Overview

Korean stock monitoring/alerting app over the **Kiwoom** REST API. Polls endpoints, stores data in `DataStore`, fires `BaseAlert` subclasses via Telegram when conditions are met.

Data flow at a glance: `KiwoomEndpoint` enum -> `REQUEST_REGISTRY` -> Request (auth-aware) -> `KiwoomSubscription` (executes) -> typed Response -> `DataStore` (SQLite) + `alert.ingest()` -> `alert.evaluate()` -> `TelegramBot.notify()`.

## Code Style

- **Python 3.12+**: `X | Y` unions, `match`, `kw_only` dataclasses, `from __future__ import annotations`
- **Ruff** for linting ([pyproject.toml](pyproject.toml))
- Korean for domain descriptions and enum metadata; English for all code identifiers
- Private attributes: `_` prefix, initialized in `__init__`; `TYPE_CHECKING` guard for circular imports
- Booleans: `is_`/`has_`/`can_` prefix
- Type hints: `str | None` not `Optional[str]`; no string-quoted type hints
- Backticks in log/exception/docstring strings (e.g., `` `KiwoomAuth.get_rest_headers()` ``)

## General Instructions

- Keep relevant existing comments when modifying code
- Suggest style improvements (renaming, etc.), but ONLY when appropriate
- For large changes (new modules, breaking changes), consult [.claude/architecture.md](.claude/architecture.md) for project structure and [.claude/design-notes.md](.claude/design-notes.md) for design rationale
