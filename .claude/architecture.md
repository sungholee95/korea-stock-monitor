# Architecture

> **Living document** — update as design decisions are made and components are implemented.

## Project Goal

Korean stock monitoring/alerting app connecting to **Kiwoom** and **KIS** APIs. Polls REST endpoints, stores data in `DataStore`, fires `BaseAlert` subclasses via Telegram when conditions are met. **Primary focus: Kiwoom adapter. KIS development paused.**

---

## Current State

### Implemented ✅

| Module | What's done |
|--------|-------------|
| `adapters/_base/` | `Config`, `Auth`, `Endpoint` ABCs; `Method` enum; `EndpointError` |
| `adapters/kis/` | `KISConfig`, `KISAuth`, `KISClient`, `KISEndpoint` + endpoints (`inquire_price`, `volume_rank`) |
| `adapters/kiwoom/` | `KiwoomConfig`, `KiwoomAuth`, `KiwoomClient`, `KiwoomEndpoint` + endpoints (`rkinfo`) |
| `core/protocols.py` | `RestResponseOutput`, `RestResponse`, `DataclassInstance` structural Protocols |
| `core/datastore.py` | `DataStore` — in-memory rows, `from_endpoint()`, `update()`, `to_polars()`, `save_to_disk()`, `from_disk()`, `get_col_index()` |
| `core/alerts.py` | `BaseAlert` ABC (`ingest`, `evaluate`, `format_message`, `check`, `is_due`); `TradeValue` concrete alert |
| `core/market_time.py` | `bucket_start(when, minutes)` — KST-anchored time bucket utility |
| Tests | `tests/adapters/kis/`, `tests/adapters/kiwoom/`, `tests/core/` |

### Stubbed / Incomplete ⚠️

- `_KISWebSocketClient` / `_KiwoomWebSocketClient` — raise `NotImplementedError`
- `adapters/telegram/` — stub only
- Pagination — `has_next_page()` detection works; auto-fetch not implemented (warns, returns first page)
- KIS alert integration — `KISClient.start()` calls `alert.check(self.datastores)` but `BaseAlert.check()` takes no args; deferred until KIS resumes

---

## File Structure

```
ksmonitor/
├── adapters/
│   ├── _base/           # Config, Auth, Endpoint ABCs; Method enum; EndpointError
│   ├── _shared/         # Cross-adapter primitives
│   ├── kis/             # KISConfig, KISAuth, KISClient, endpoints/
│   ├── kiwoom/          # KiwoomConfig, KiwoomAuth, KiwoomClient, endpoints/
│   └── telegram/        # Stub
├── core/
│   ├── protocols.py     # RestResponseOutput, RestResponse structural Protocols
│   ├── datastore.py     # DataStore: SQLite + in-memory + Polars
│   ├── alerts.py        # BaseAlert ABC + TradeValue
│   └── market_time.py   # KST bucket_start()
└── tools/
    └── first_use.py     # Partial: folder setup done, credential storage incomplete
```

Each adapter's `endpoints/` package: `_common.py` (enum + `REQUEST_REGISTRY`), `_base.py` (ABCs), one module per endpoint.

---

## Data Flow

```
Kiwoom API ──→ _KiwoomRestClient.poll()
                       │
              ╔════════╧════════╗
         _poll_loop         _alert_loop
              │                 │
    DataStore.update()     alert.is_due()?
    DataStore.save()            │
    alert.ingest()         alert.check() → print() [TODO: Telegram]
```

`KiwoomClient.start()` runs both loops concurrently via `asyncio.gather`. Alert `evaluate()` reads only cached state — never scans DataStore.

---

## KIS vs Kiwoom Differences

| Aspect | KIS | Kiwoom |
|--------|-----|--------|
| Endpoint ID field | `tr_id` | `api_id` |
| Request method | GET or POST | POST only |
| Response OK | `rt_cd == "0"` | `return_code == 0` |
| Pagination | `tr_cont` header + context area keys | `cont_yn` + `next_key` header |
| Response output key | `"output"` (always) | Varies per endpoint via `_output_key` ClassVar |
| WS approval key | Separate `/oauth2/Approval` flow | Not needed |
| Keyring service | `"kis"` | `"kiwoom"` |
| Token expiry field | `access_token_token_expired` | `expires_dt` (`%Y%m%d%H%M%S`) |

---

## Build Order

| Priority | Component | Status |
|----------|-----------|--------|
| ~~P1~~ | Response handling | ✅ Done |
| ~~P2~~ | `DataStore` | ✅ Done |
| ~~P4~~ | `core/alerts.py` + alert integration (Kiwoom) | ✅ Done |
| **P3** | Pagination auto-fetch | `has_next_page()` done; auto-fetch not yet |
| **P5** | `adapters/telegram/bot.py` | Replace `print(message)` in `_alert_loop` |
| **P7** | WebSocket client | `_KiwoomWebSocketClient` + request/response classes |
| **P8** | New endpoints + alerts | Add as needed |

See `design-notes.md` for detailed plans on P3, P5, P7.

---

## Design Decisions

- **`adapters/_base/` ABCs + `core/protocols.py` Protocols** — adapters implement ABCs; `core/` uses structural Protocols, never adapter types directly
- **`__init_subclass__` auto-registration** — endpoint classes self-register into `REQUEST_REGISTRY`; adding an endpoint = define classes + import in `__init__.py`
- **Typed response schemas mandatory** — every endpoint has a `ResponseOutput` subclass; no generic fallback
- **OOP stateful `BaseAlert` subclasses** — rolling aggregates need encapsulated state; callable dataclass approach would have required external state management
- **Adapter-specific clients** (`KISClient` / `KiwoomClient`) — alert integration patterns diverge between adapters; a shared `Client` would have forced awkward abstractions
- **`ingest` / `evaluate` split** — `ingest()` runs every poll; `evaluate()` runs on its own `eval_interval` via `_alert_loop`; decouples alert cadence from REST poll rate
- **Sync `requests`** — single-user local app; no concurrency pressure on REST calls
- **SQLite + Polars** — zero-infrastructure persistence; Polars for in-memory DataFrame analysis
- **Credentials in keyring; API URLs hardcoded** — prevents YAML-based credential hijacking
