# Architecture

> **Living document** — update as design decisions are made and components are implemented.

## Project Goal

Korean stock monitoring/alerting app over the **Kiwoom** REST API. Polls endpoints, persists data in `DataStore`, fires `BaseAlert` subclasses via Telegram when conditions are met.

---

## Current State

### Implemented ✅

| Module | What's done |
|--------|-------------|
| `adapters/_shared.py` | `Method` enum, `EndpointError` |
| `adapters/kiwoom/` | `KiwoomConfig`, `KiwoomAuth`, `KiwoomClient`, `KiwoomEndpoint` + endpoints (`rkinfo`) |
| `adapters/telegram/` | `TelegramBot` — command handlers, alert register/unregister, dispatch via `notify()`, persistent subscriptions in `core.yaml` |
| `core/protocols.py` | `RestResponseOutput`, `RestResponse`, `DataclassInstance` Protocols |
| `core/datastore.py` | `DataStore` — monolithic per-client store; one SQLite file with one table per subscription, addressed by name; retention sweep on init |
| `core/alerts.py` | `BaseAlert` ABC + `TradeValue` concrete alert (per-ticker cooldown) |
| `core/market_time.py` | `bucket_start`, `bucket_index` (KST-anchored) |
| `main.py` | Orchestrator — wires `KiwoomClient.poll_loop` + `dispatch_alerts` + `TelegramBot.start_bot` via `asyncio.gather` |

### Stubbed / Incomplete ⚠️

- WebSocket client — `_KiwoomWebSocketClient.subscribe()` raises `NotImplementedError`
- Pagination auto-fetch — `has_next_page()` detection works; on a paged response the client logs a warning and returns the first page only

---

## File Structure

```
ksmonitor/
├── adapters/
│   ├── _shared.py       # Method enum, EndpointError
│   ├── kiwoom/          # KiwoomConfig, KiwoomAuth, KiwoomClient, endpoints/
│   └── telegram/        # TelegramBot (command handlers, dispatch, persistence)
└── core/
    ├── protocols.py
    ├── datastore.py
    ├── alerts.py
    └── market_time.py
```

The `endpoints/` package: `_common.py` (enum + `REQUEST_REGISTRY`), `_base.py` (ABCs), one module per endpoint.

`main.py` at the repo root is the orchestrator entry point. `scratches/` holds throwaway experiments.

---

## Endpoint Registration

`KiwoomEndpoint` enum values are routing IDs (e.g., `"ka10032"`). Adding an endpoint:

1. Add enum member in `endpoints/_common.py`
2. Create module with `*Request`, `*Response`, `*ResponseOutput` dataclasses — `KiwoomBaseRestRequest.__init_subclass__` auto-registers into `REQUEST_REGISTRY`; `*ResponseOutput` fields are `field(default_factory=list, init=False, metadata={"ko": ...})` and populated by `__post_init__` parsing `output_raw`
3. Import in `endpoints/__init__.py`

`*Response` subclasses set `_output_key` (e.g., `"trde_prica_upper"`) — the body key that holds the array Kiwoom returns. The `{"ko": "한글명"}` field metadata drives both the human-readable column naming in `DataStore` and any future schema-drift detection.

---

## DataStore

One `DataStore` per client owns one SQLite file with one table per subscription, addressed by name. `register(name, schema)` creates the table and infers columns from `metadata={"ko": ...}` fields. `update(name, output)` buffers rows; `save(name?)` flushes to SQLite. `unregister(name)` drops the in-memory state but preserves the table. On init, a retention sweep deletes rows with `polled_at` older than `retention_days` (default 7 days) from every table. `update()` after `unregister()` is a logged no-op — race-safe by design.

Alerts read only their in-memory caches populated by `ingest()`, never the `DataStore`.

The connection is opened with `check_same_thread=False` and guarded by a `threading.Lock`, plus WAL mode, so the asyncio loop and any executor threads can share it safely.

---

## Auth & Credentials

Secrets live in Windows Credential Manager via `keyring` (service: `"kiwoom"`). The Kiwoom config YAML at `~/.ksmonitor/config/kiwoom.yaml` only holds non-secret identifiers and is whitelisted on load to prevent injection of unknown keys. API base URLs are hardcoded as class attributes on `KiwoomConfig` — never read from YAML — to prevent hijacking.

Telegram per-chat alert subscriptions are persisted to `~/.ksmonitor/config/core.yaml` (atomic tmp + `os.replace`); only the bot token lives in keyring (the keyring service name itself is read from `core.yaml` under `telegram.bot.svc_name`).

---

## Rate Limits

- Production: ≤ 20 REST calls/s; Paper (모의): ≤ 2 REST calls/s
- `_KiwoomRestClient._enforce_rate_limit()` runs at the end of every `subscribe()` call, after the new subscription is registered. The check is `n_subscriptions / poll_rate ≤ limit`.

---

## Data Flow

```
Kiwoom API ──→ _KiwoomRestClient.poll()
                       │
              ╔════════╧═════════════════════╗
         poll_loop                       alert_loop
              │                              │
    DataStore.update(name)              alert.is_due()?
    DataStore.save()                         │
    alert.ingest()                      alert.check() ──→ yield (alert, message)
                                                              │
                                                       dispatch_alerts()
                                                              │
                                                     TelegramBot.notify(alert, msg)
```

`main.start()` runs `poll_loop`, `dispatch_alerts`, and `bot.start_bot` together via `asyncio.gather`. `alert_loop` is an async generator yielding `(alert, message)` tuples; `dispatch_alerts` consumes them and forwards to `TelegramBot.notify`, which fans out to every `chat_id` subscribed to that alert. Alert evaluation reads only the cache populated by `ingest()` — never scans `DataStore`.

`alert_loop` sleeps until `min(alert.next_eval_time(now))`, interruptible by `_alerts_changed.set()` so newly registered/unregistered alerts take effect immediately.

---

## Alert Registration

Alerts carry their target `endpoint` (+ optional `endpoint_params`) directly. `KiwoomClient.register_alerts(*alerts)` derives a subscription key from the endpoint name and params (sorted), auto-subscribes if needed (creating the `DataStore` table from the response schema), and routes incoming responses to the matching alerts via `_alerts_by_sub`. `unregister_alert` reverses both the alert routing and the underlying subscription if no other alert needs it.

Alert identity is value-based on `(type_key, spec())` — two `TradeValue` instances with the same args are interchangeable as dict/set keys, so re-registering across restarts is idempotent.

`TelegramBot` wraps these as the `/alert <type> <args...>` and `/unalert <type> <args...>` commands. Per-chat subscriptions are persisted to `~/.ksmonitor/config/core.yaml` (atomic tmp + `os.replace`) and reloaded on startup, so users don't have to re-register after a restart. `ALERTS_REGISTRY` in `adapters/telegram/bot.py` maps user-facing Korean alert names (e.g. `"거래대금"`) to `BaseAlert` subclasses.

---


## Build Order

| Priority | Component | Status |
|----------|-----------|--------|
| ~~P1~~ | Response handling | ✅ Done |
| ~~P2~~ | `DataStore` v1 | ✅ Done |
| ~~P3b~~ | `DataStore` rewrite (monolithic, retention sweep) + re-enabled `poll_loop` persistence | ✅ Done |
| ~~P4~~ | `core/alerts.py` + Kiwoom integration | ✅ Done |
| ~~P5~~ | Telegram dispatch | ✅ Done (`TelegramBot` with persistent per-chat subscriptions) |
| ~~P6~~ | Endpoint-driven alert registration | ✅ Done |
| **P3** | Pagination auto-fetch | Detection done; auto-fetch pending |
| **P7** | WebSocket client | `_KiwoomWebSocketClient` + WS request/response classes |
| **P8** | New endpoints + alerts | As needed |

---

## Design Decisions

- **No shared Config/Auth/Endpoint ABCs.** `adapters/_shared.py` only holds `Method` and `EndpointError`. `core/` stays adapter-agnostic via `core/protocols.py` structural types.
- **`__init_subclass__` auto-registration.** Endpoint classes self-register into `REQUEST_REGISTRY`; adding an endpoint = define classes + import.
- **Typed response schemas, no generic fallback.** Every endpoint has a `ResponseOutput` subclass with Korean field metadata driving both schema drift detection and `DataStore` column naming.
- **OOP stateful alerts.** `BaseAlert` subclasses encapsulate per-ticker rolling state; a callable approach would push that state outward.
- **Alerts subscribe to endpoints, not subscription names.** Removes the foot-gun where the user had to create the subscription before registering the alert.
- **Value-based alert identity.** `__hash__`/`__eq__` on `(type_key, spec())` so re-registering after a restart (or re-issuing `/alert` from another chat) is idempotent.
- **`evaluate()` returns an event payload, not a bool.** `format_message(event)` then renders it. `TradeValue` returns the list of fired tickers.
- **`ingest` / `evaluate` split.** `ingest` runs every poll; `evaluate` runs on the alert's own `is_due` / `next_eval_time` schedule. Alert cadence is decoupled from REST poll rate.
- **Per-ticker cooldown for `TradeValue`.** `TradeValue` overrides `check()` so cooldown is tracked per ticker instead of for the whole alert; one ticker firing doesn't gag others.
- **`alert_loop` as async generator, not direct dispatch.** The client yields `(alert, message)` events; `main.py` wires them to `TelegramBot.notify`. Keeps `KiwoomClient` unaware of the transport.
- **SQLite for persistence; no Polars.** Analysis happens elsewhere; the live path doesn't need a DataFrame layer.
- **Credentials in keyring; API URLs hardcoded.** Prevents YAML-based credential hijacking.
