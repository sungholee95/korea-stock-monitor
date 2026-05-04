# Architecture

> **Living document** — update as design decisions are made and components are implemented.

## Project Goal

Korean stock monitoring/alerting app connecting to **Kiwoom** and **KIS** APIs. Polls REST endpoints, stores data in `DataStore`, fires `BaseAlert` subclasses via Telegram when conditions are met. **Primary focus: Kiwoom adapter. KIS development paused.**

---

## Current State

### Implemented ✅

| Module | What's done |
|--------|-------------|
| `adapters/_shared.py` | `Method` enum, `EndpointError` |
| `adapters/kis/` | `KISConfig`, `KISAuth`, `KISClient`, `KISEndpoint` + endpoints (`inquire_price`, `volume_rank`) |
| `adapters/kiwoom/` | `KiwoomConfig`, `KiwoomAuth`, `KiwoomClient`, `KiwoomEndpoint` + endpoints (`rkinfo`) |
| `core/protocols.py` | `RestResponseOutput`, `RestResponse`, `DataclassInstance` Protocols |
| `core/datastore.py` | `DataStore` — in-memory rows + SQLite + Polars |
| `core/alerts.py` | `BaseAlert` ABC + `TradeValue` concrete alert |
| `core/market_time.py` | `bucket_start`, `bucket_index` (KST-anchored) |

### Stubbed / Incomplete ⚠️

- WebSocket clients — `subscribe()` raises `NotImplementedError`
- Telegram dispatch — stub; `_alert_loop` still uses `print(message)`
- Pagination auto-fetch — `has_next_page()` works; auto-fetch warns and returns first page
- `KISClient` — no alert integration (paused)
- No `monitor.py` orchestrator; `run_kiwoom.py` / `run_kis.py` are manual entry points

---

## File Structure

```
ksmonitor/
├── adapters/
│   ├── _shared.py       # Method enum, EndpointError
│   ├── kis/             # KISConfig, KISAuth, KISClient, endpoints/
│   ├── kiwoom/          # KiwoomConfig, KiwoomAuth, KiwoomClient, endpoints/
│   └── telegram/        # Stub
└── core/
    ├── protocols.py
    ├── datastore.py
    ├── alerts.py
    └── market_time.py
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
    alert.ingest()         alert.check() -> print() [TODO: Telegram]
```

`KiwoomClient.start()` runs both loops via `asyncio.gather`. `_alert_loop` sleeps until `min(alert.next_eval_time(now))`, then calls `check()` on every alert with `is_due(now) == True`. Alert evaluation reads only the cache populated by `ingest()` — never scans `DataStore`.

---

## Alert Registration

Alerts carry their target `endpoint` (+ optional `endpoint_params`) directly. `KiwoomClient.register_alerts(*alerts)` derives the subscription key, auto-subscribes if needed (creating the `DataStore` from the response schema), and routes incoming responses to the matching alerts via `_alerts_by_sub`.

---

## KIS vs Kiwoom Differences

| Aspect | KIS | Kiwoom |
|--------|-----|--------|
| Endpoint ID field | `tr_id` | `api_id` |
| Request method | GET or POST | POST only |
| Response OK | `rt_cd == "0"` | `return_code == 0` |
| Pagination | `tr_cont` header + context area keys | `cont_yn` + `next_key` header |
| Response output key | `"output"` (always) | Varies per endpoint via `_output_key` |
| WS approval key | Separate `/oauth2/Approval` flow | Not needed |
| Keyring service | `"kis"` | `"kiwoom"` |
| Token expiry field | `access_token_token_expired` | `expires_dt` (`%Y%m%d%H%M%S`) |
| Alert integration | None (paused) | Full: `register_alerts`, dual async loop |

---

## Build Order

| Priority | Component | Status |
|----------|-----------|--------|
| ~~P1~~ | Response handling | ✅ Done |
| ~~P2~~ | `DataStore` | ✅ Done |
| ~~P4~~ | `core/alerts.py` + Kiwoom integration | ✅ Done |
| ~~P6~~ | Endpoint-driven alert registration | ✅ Done |
| **P3** | Pagination auto-fetch | Detection done; auto-fetch pending |
| **P5** | Telegram dispatch | Replace `print(message)` |
| **P7** | WebSocket client | `_KiwoomWebSocketClient` + WS request/response classes |
| **P8** | New endpoints + alerts | As needed |

---

## Design Decisions

- **No shared Config/Auth/Endpoint ABCs.** An earlier `adapters/_base/` package was collapsed to `_shared.py` (just `Method` + `EndpointError`). The two adapters diverged enough that the ABCs added indirection without payoff. `core/` stays adapter-agnostic via `core/protocols.py` structural types.
- **`__init_subclass__` auto-registration.** Endpoint classes self-register into `REQUEST_REGISTRY`; adding an endpoint = define classes + import.
- **Typed response schemas, no generic fallback.** Every endpoint has a `ResponseOutput` subclass with Korean field metadata driving both schema drift detection and `DataStore` column naming.
- **OOP stateful alerts.** `BaseAlert` subclasses encapsulate per-ticker rolling state; a callable approach would push that state outward.
- **Alerts subscribe to endpoints, not subscription names.** Removes the foot-gun where the user had to create the subscription before registering the alert.
- **`evaluate()` returns an event payload, not a bool.** `format_message(event)` then renders it. `TradeValue` returns the list of fired tickers.
- **Adapter-specific clients.** Alert integration patterns diverge enough between KIS and Kiwoom that a shared `Client` would force awkward abstractions.
- **`ingest` / `evaluate` split.** `ingest` runs every poll; `evaluate` runs on the alert's own `is_due` / `next_eval_time` schedule. Alert cadence is decoupled from REST poll rate.
- **Sync `requests`.** Single-user local app; no concurrency pressure on REST calls.
- **SQLite + Polars.** Zero-infrastructure persistence; Polars for in-memory analysis.
- **Credentials in keyring; API URLs hardcoded.** Prevents YAML-based credential hijacking.
