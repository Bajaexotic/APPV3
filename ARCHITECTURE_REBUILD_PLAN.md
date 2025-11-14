# APPSIERRA Architecture Rebuild Plan

  This document captures the target architecture and concrete refactor plan for converging the codebase to a clean,
  layered, event‑driven design:

  > **DTC → Services → State → Panels**

  The goal is:
  - UI is *only* a projection layer (no domain logic, no persistence).
  - Services own business rules and persistence.
  - StateManager owns coherent in‑memory state, not storage.
  - DTC integration is an adapter feeding domain events into the system.
  - There is one messaging system (SignalBus) and one balance/position truth (database).

  All sections below are written to be executable as a sequence of changes, not abstract guidance.

  ---

  ## 1. Reconstruct the Correct Architecture

  ### 1.1 Target Layering

  **External / Integration**
  - `services/dtc_protocol.py`, `services/dtc_constants.py`, `services/dtc_schemas.py`
    - Pure protocol encoding/decoding.
  - `core/data_bridge.py::DTCClientJSON`
    - DTC adapter: owns sockets, framing, handshake.
    - Emits *only* domain‑oriented events onto `SignalBus`.

  **Services (Domain + Persistence)**
  - **Trade / Position services**
    - `services/trade_service.py` (TradeManager) – trade recording and balance update.
    - `data/position_repository.py` – persistence only; no UI, no StateManager access.
    - **New** `services/position_service.py` (or extend `TradeManager`) – orchestrates open/close of positions:
      - Subscribes to `SignalBus` events (order/position messages and UI intents).
      - Uses `PositionRepository` + `TradeManager` to mutate DB + balances.
      - Emits `SignalBus.positionOpened/Updated/Closed` and `SignalBus.tradeClosedForAnalytics`.
  - **Balance service**
    - Either:
      - Integrated into `TradeManager` (recommended), or
      - A dedicated `services/balance_service.py`.
    - Responsible for:
      - Maintaining SIM/LIVE balances in DB (via ledger) and pushing updates to StateManager.
      - Emitting `SignalBus.balanceUpdated` with canonical values.
  - **Stats service**
    - `services/stats_service.py` – sole owner of statistics and timeframe P&L.
  - **Recovery**
    - `services/position_recovery.py` – uses repository to reconstruct state; no UI or DTC logic inside.

  **State**
  - `core/state_manager.py`
    - Single in‑memory view of:
      - Current mode + account.
      - “Active trade” metadata (what mode is currently in a trade).
      - Current SIM/LIVE balances.
    - Should **not**:
      - Talk directly to DB.
      - Own persistent JSON files.
    - Receives:
      - Mode updates from services (not from panels).
      - Balance updates from `TradeManager`/Balance service.
      - Position open/close metadata as needed to enforce invariants (“one position at a time”).

  **UI / Panels**
  - `panels/panel1.py`, `panels/panel2.py`, `panels/panel3.py`
    - Subscribe to `SignalBus` and `StateManager` signals.
    - Render what they are told; may expose *read‑only* queries to services (through signals or small facades) but do
  not own persistence or domain rules.
    - Panel2:
      - Owns no DB calls.
      - Uses `domain/position.Position` only as a view model (constructed from canonical state).
    - Panel1:
      - Reads balance exclusively from `StateManager` (or a small read‑service), never from JSON.
      - Reads stats exclusively from `stats_service`.
    - Panel3:
      - Reads stats and trade analytics exclusively from `stats_service` / analytics signals.

  ### 1.2 Target Event Flow

  **Inbound from DTC**
  1. `DTCClientJSON` receives frames and decodes DTC JSON.
  2. `_dtc_to_app_event()` normalizes protocol to app events:
     `TRADE_ACCOUNT`, `BALANCE_UPDATE`, `POSITION_UPDATE`, `ORDER_UPDATE`, etc.
  3. `_emit_app()`:
     - Emits **only** SignalBus events:
       - `tradeAccountReceived(dict)`
       - `balanceUpdated(balance: float, account: str)`
       - `positionUpdated(dict)`
       - `orderUpdateReceived(dict)`
     - No Blinker, no direct panel calls, no router.

  **Within the app**
  4. Services subscribe to SignalBus:
     - Position/Trade service:
       - `orderUpdateReceived` → interprets fills; updates repository and balances.
       - `positionUpdated` → tracks open positions in DB; may emit derived events.
     - Balance service:
       - `balanceUpdated` (from DTC for LIVE) → reconciles with DB and updates StateManager.
  5. StateManager:
     - Receives mode decisions from services (e.g. `PositionService` or DTC adapter via a mode‑decision service).
     - Receives balance changes only from Balance service / TradeManager.
     - Emits `state.modeChanged` and `state.balanceChanged`.
     - A thin bridge forwards `state.modeChanged` as `SignalBus.modeChanged`.

  **Outbound to UI**
  6. Panels subscribe to:
     - `SignalBus.positionOpened/Updated/Closed` and `tradeClosedForAnalytics`.
     - `SignalBus.balanceUpdated` or `StateManager.balanceChanged` (but not DTC raw).
     - `SignalBus.dtcConnected/dtcDisconnected/dtcSessionReady` for connection indicators.
     - `SignalBus.themeChangeRequested` / `timeframeChangeRequested` for UI coordination.
  7. Panels emit only **intents**:
     - `SignalBus.orderSubmitRequested(dict)` – user wants to place order.
     - `SignalBus.positionCloseRequested(mode, account)` (new) – user wants to close current position.
     - `SignalBus.modeSwitchRequested(str)` – user changes trading mode.

  In all cases, persistence and business decisions sit inside services, not panels.

  ---

  ## 2. Critical Issues – Exact Fixes

  For each issue: **root cause**, **correction**, **modules**, **minimal refactors**, **order**.

  ### 2.1 SIM Balance – Multiple Sources of Truth

  **Root cause**
  - SIM balance exists simultaneously as:
    - `StateManager.sim_balance` (`core/state_manager.py`).
    - Per‑account JSON files (`core/sim_balance.py` / `sim_balance_{account}.json`).
    - Implicitly via trades ledger in DB (used by `load_sim_balance_from_trades()`).
  - Panel1 uses `get_sim_balance(account)` to display balances (`panels/panel1.py:1120-1185`), while StateManager uses
  DB on startup.
  - Reset hotkey uses both StateManager and `SimBalanceManager`, and the fallback call is invalid (`mgr.reset_balance()`
  without account).

  **Correction**
  - Declare **database + trades ledger** as *the* source of SIM balance.
  - StateManager is the in‑memory cache, fed only from DB and services.
  - `core/sim_balance.py` is demoted or removed from runtime path.
  - Panel1 only reads from StateManager (or a balance read‑service), never from JSON.

  **Modules to change**
  - `core/state_manager.py`
  - `core/app_manager.py::_setup_state_manager`, `_on_reset_sim_balance_hotkey`
  - `core/sim_balance.py`
  - `panels/panel1.py` (SIM balance functions)
  - `services/trade_service.py` (ensure it updates balance)

  **Minimal refactors**
  1. **StateManager as balance cache**
     - Keep `load_sim_balance_from_trades()` as the single startup initializer.
     - Ensure `TradeManager.record_closed_trade()` always calls `state.set_balance_for_mode("SIM", new_balance)` for SIM
  trades (this already happens but must be used consistently).
  2. **Panel1 balance retrieval**
     - Change Panel1’s `set_trading_mode` / `_on_mode_changed` paths to read SIM balance from:
       - `state.get_balance_for_mode("SIM")` only.
     - Remove calls to `get_sim_balance(account)` for live UI.
  3. **Reset hotkey**
     - `_on_reset_sim_balance_hotkey`:
       - Call a new service or StateManager method that:
         - Resets the underlying ledger (e.g., by inserting a synthetic “reset” transaction or by clearing trades +
  resetting starting balance).
         - Or, simpler: set `sim_balance` to 10k in StateManager and emit a `balanceUpdated` event; let DB ledger remain
  as history, but mark reset via an audit record.
       - Remove usage of `get_sim_balance_manager()`.
  4. **SimBalanceManager**
     - Either:
       - Restrict it to *offline tools/tests only*, or
       - Remove it entirely once all references are gone.

  **Order**
  1. Remove Panel1’s dependency on `get_sim_balance()`.
  2. Fix/reset hotkey to operate purely via StateManager/DB.
  3. Ensure TradeManager balance updates are the only SIM balance mutations.
  4. Deprecate/remove `core/sim_balance.py` from runtime.

  ---

  ### 2.2 Position Closing Bypasses StateManager and Services

  **Root cause**
  - `Panel2.notify_trade_closed()` calls `_close_position_in_database()` directly (`panels/panel2.py:333-420`), which
  uses `PositionRepository.close_position(mode=self.current_mode, account=self.current_account, ...)`.
  - StateManager’s position fields and balance logic are not part of this closure pipeline.
  - Only if `_close_position_in_database()` fails does Panel2 fall back to `TradeManager.record_closed_trade()`.

  **Correction**
  - Introduce a `TradeCloseService` (or extend `TradeManager`) that owns the trade closure pipeline:
    - Subscribed to a new UI intent: `SignalBus.positionCloseRequested(mode, account, context)` or
  `tradeCloseRequested(trade_dict)`.
    - Uses `PositionRepository.close_position(...)` for DB updates.
    - Computes/updates balances via StateManager.
    - Emits `SignalBus.positionClosed` / `tradeClosedForAnalytics`.
  - Panel2 no longer calls repositories or TradeManager directly; it emits an intent and listens for closure events to
  update its UI.

  **Modules to change**
  - `panels/panel2.py`
  - `data/position_repository.py`
  - `services/trade_service.py` (or new `services/position_service.py`)
  - `core/state_manager.py` (ensure position metadata is updated)
  - `core/signal_bus.py` (new intent/closure signals)

  **Minimal refactors**
  1. Add new signals to `SignalBus`:
     - `tradeCloseRequested = pyqtSignal(dict)` (UI intent) – or `positionCloseRequested(mode, account)`.
     - `positionClosed = pyqtSignal(dict)` – high‑level closed position details (mode, account, symbol, P&L).
  2. Implement `TradeCloseService`:
     - Subscribes to `tradeCloseRequested`.
     - Validates mode/account vs StateManager.
     - Calls `PositionRepository.close_position(...)` with canonical mode/account from StateManager.
     - Updates balances via `state.set_balance_for_mode(mode, new_balance)`.
     - Emits `positionClosed` and `tradeClosedForAnalytics`.
  3. Rewrite `Panel2.notify_trade_closed()`:
     - Constructs a `trade` dict with UI context (symbol, entry/exit prices, etc.).
     - Emits `SignalBus.tradeCloseRequested(trade)`.
     - Removes direct calls to `_close_position_in_database` and `_close_position_legacy`.
     - Listens to `positionClosed` and `tradeClosedForAnalytics` for UI/Panel3 updates.
  4. Reduce StateManager’s `close_position()` to a pure in‑memory state reset, called by services after DB close.

  **Order**
  1. Add new intent/closure signals to `SignalBus`.
  2. Implement `TradeCloseService` and wire it to SignalBus.
  3. Convert `Panel2.notify_trade_closed()` to emit intents instead of doing persistence.
  4. Remove `_close_position_in_database` and `_close_position_legacy` from Panel2.

  ---

  ### 2.3 Panels Owning Domain Logic (God‑Object Behavior)

  **Root cause**
  - Panel2:
    - Maintains full position state (via `domain.position.Position` and legacy fields).
    - Owns trade timers, MAE/MFE extremes persistence to JSON, and trade closure orchestration.
    - Talks directly to repositories and legacy `TradeManager`.
  - Panel1:
    - Queries DB directly for timeframe P&L and builds equity curves.
  - Panel3:
    - Directly queries DB (via stats service) *and* accesses Panel2’s live state.

  **Correction**
  - The domain model (`domain/position.Position`) and repositories remain, but are orchestrated in services.
  - Panels:
    - Receive fully-formed view models from services/state via signals or thin read APIs.
    - Optionally use `Position` only as a view model, never as authoritative state/persistence driver.

  **Modules to change**
  - `panels/panel2.py`
  - `panels/panel1.py`
  - `panels/panel3.py`
  - `domain/position.py` (possibly add view‑friendly helpers; no UI changes here)
  - `services/stats_service.py`
  - New/extended trade/position services.

  **Minimal refactors**
  1. Panel2:
     - Strip out DB and repository calls and trade closure logic (as per 2.2).
     - Limit JSON persistence to *UI‑only* ephemeral state (timers) if retained.
     - Have Panel2 subscribe to:
       - `SignalBus.positionOpened/Updated/Closed` to update its view model.
       - `SignalBus.priceUpdated` for live price feed (future).
  2. Panel1:
     - Use `services/stats_service.compute_trading_stats_for_timeframe()` exclusively for timeframe P&L and metrics.
     - Do not access `get_session()` directly.
  3. Panel3:
     - Continue using `stats_service` for historical metrics.
     - Use only `tradeClosedForAnalytics` / `positionClosed` for per‑trade analytics – no direct access to Panel2’s
  internal state.

  **Order**
  1. Implement service‑side equivalents of Panel1’s P&L calculations (most already exist in `stats_service`).
  2. Convert Panel1 to use `stats_service` only; remove direct DB access.
  3. Convert Panel2 to rely on service events for position updates and trade closure.
  4. Untangle Panel3 from Panel2 by routing everything through services.

  ---

  ### 2.4 Mode Isolation Inconsistencies

  **Root cause**
  - Mode is derived in multiple places (`utils.trade_mode`, Panel2, StateManager, DTC pipelines).
  - `Panel2.notify_trade_closed()` uses `detect_mode_from_account(trade["account"])`, but repository calls use
  `self.current_mode/current_account` which may not match the account reflected in the trade.
  - Mode signals come from StateManager but there is also a dormant `SignalBus.modeChanged`.

  **Correction**
  - Single source of truth for mode:
    - `utils.trade_mode.detect_mode_from_account()` used *only at the integration boundary* (DTC and user actions).
    - Mode decisions are applied in **one** place (e.g. a ModeResolver service or StateManager).
    - All other components consume `state.current_mode` + `state.current_account`.

  **Modules to change**
  - `core/state_manager.py`
  - `utils/trade_mode.py`
  - `core/data_bridge.py` (where mode is first seen in DTC messages)
  - `panels/panel2.py` (mode in `notify_trade_closed`, `_load_position_from_database`)
  - `services/position_recovery.py`

  **Minimal refactors**
  1. Introduce a `ModeResolver` responsibility (could be a small function or service):
     - DTC messages with `TradeAccount` → `ModeResolver` → `state.set_mode(account)`.
  2. Ensure:
     - Services and Panel2 always use `state.current_mode/current_account` when interacting with repositories.
     - Panel2 uses `state.current_mode/current_account` instead of recomputing from trade dicts.
  3. Emit a single `modeChanged` chain:
     - StateManager emits `modeChanged`.
     - A thin bridge in a small module or `app_manager` listens to `state.modeChanged` and emits
  `SignalBus.modeChanged`.
     - Panels subscribe only to `SignalBus.modeChanged` (or only to StateManager; pick one and stick with it).

  **Order**
  1. Ensure all DB operations use `state.current_mode/current_account`.
  2. Remove redundant mode detection from Panel2 and any other consumers.
  3. Wire modeChanged through a single pipeline (StateManager → SignalBus → Panels).

  ---

  ### 2.5 Hard‑coded File Paths

  **Root cause**
  - `CSV_FEED_PATH` in `panels/panel2.py:24` is an absolute path to a user‑specific directory.

  **Correction**
  - Move all paths into `config/settings.py` (or an equivalent configuration module) and reference them there.

  **Modules to change**
  - `panels/panel2.py`
  - `config/settings.py` (or create a central config if not present)

  **Minimal refactors**
  1. Add `SNAPSHOT_CSV_PATH` to `config/settings.py` with a default relative path (`data/snapshot.csv`).
  2. Change Panel2 to import `SNAPSHOT_CSV_PATH` and use it instead of the hard‑coded absolute path.
  3. Optionally, allow overrides via env vars.

  **Order**
  1. Add config setting.
  2. Replace constant in Panel2.

  ---

  ### 2.6 Mixed Messaging Systems (Blinker + SignalBus)

  **Root cause**
  - `core/data_bridge.py` emits both Blinker and SignalBus events.
  - SignalBus is the intended direction; Blinker remains from earlier iterations and is still live in tests and docs.

  **Correction**
  - Make SignalBus **the only** runtime event bus.

  **Modules to change**
  - `core/data_bridge.py`
  - `core/signal_bus.py`
  - Any tests/tools using Blinker signals in production scenarios.

  **Minimal refactors**
  1. In `_emit_app()`:
     - Remove all `signal_* .send(...)` calls.
     - Keep only SignalBus emissions.
  2. Remove or gate the Blinker signals:
     - Either delete `signal_trade_account`, `signal_balance`, `signal_position`, `signal_order`, or add a clear comment
  that they exist only for backward‑compatibility CLI tools (and ensure those tools are not part of normal runtime).
  3. Update tests to subscribe to SignalBus instead of Blinker.

  **Order**
  1. Identify any production code still subscribing to Blinker (there should be none by design).
  2. Remove Blinker emissions from `_emit_app()`.
  3. Adjust tests/tools as needed.

  ---

  ### 2.7 Multiple Competing Stores for Positions

  **Root cause**
  - Position is stored in:
    - StateManager (`position_symbol`, `position_qty`, `position_mode`, etc.).
    - Panel2 `_position` domain object.
    - DB `OpenPosition` + `TradeRecord` tables.
    - JSON state files for Panel2 timers/extremes.

  **Correction**
  - Make DB `OpenPosition` the **only authoritative store** for open positions; `TradeRecord` the authoritative store
  for closed trades.
  - StateManager contains only high‑level metadata; Panel2 is a projection.
  - JSON retains only UI‑specific ephemeral information or is removed entirely.

  **Modules to change**
  - `data/position_repository.py`
  - `core/state_manager.py` (position fields and helpers)
  - `panels/panel2.py`
  - `services/position_recovery.py`

  **Minimal refactors**
  1. Declare in code/doc:
     - `OpenPosition` is the single source of truth for current trades.
  2. StateManager:
     - On open/close from services, update only:
       - `position_mode`, `position_symbol`, `position_qty`, `position_entry_price/time`.
     - Never writes to DB; just tracks invariants and emits signals.
  3. Panel2:
     - When mode/account changes or on startup, call a service (or subscribe to an event) that delivers current
  `OpenPosition` view; do not read DB directly if possible.
     - If direct DB access is kept, ensure it is only for read and uses `PositionRepository.get_open_position`.
  4. Position recovery:
     - `services/position_recovery.py` remains the only place that reconstructs in‑memory state from DB on startup.

  **Order**
  1. Use repository/state for all position open/close events.
  2. Remove panel‑side writes to position state in DB.
  3. Restrict JSON state to timers only or eliminate it if possible.

  ---

  ### 2.8 JSON vs DB Conflict for SIM Balance

  **Root cause**
  - SimBalanceManager JSON files and DB ledger both claim to represent SIM balances.
  - Panel1 uses JSON; StateManager uses DB; there is no reconciliation.

  **Correction**
  - JSON files are either:
    - Deleted (preferred), or
    - Relegated to tooling/testing and never used at runtime.
  - SIM balance is computed from DB trades + starting balance and cached in StateManager.

  **Modules to change**
  - `core/sim_balance.py`
  - `panels/panel1.py`
  - `core/app_manager.py`
  - `services/trade_service.py`

  **Minimal refactors**
  1. Stop reading JSON balances for live UI.
  2. If JSON is kept:
     - Let a one‑off migration tool read JSON and seed DB, then delete/ignore JSON thereafter.
  3. Keep only DB + StateManager as the SIM balance pipeline.

  **Order**
  1. Remove runtime reads of JSON.
  2. Remove or quarantine JSON persistence for balances.

  ---

  ## 3. Code to Remove or Merge

  ### 3.1 Obsolete or Redundant Modules

  **To delete (after confirming no imports):**
  - `core/message_router.py` – already removed but still referenced in docs; ensure all import attempts are gone.
  - Panel backups:
    - `panels/panel1_original_backup.py`
    - `panels/panel2_original_backup.py`
    - `panels/panel2_backup_before_extraction.py`
    - `panels/panel1.py.tmp`
  - Legacy helpers/tools that depend on MessageRouter for runtime behavior (leave only if used for offline analysis):
    - `tools/router_diagnostic.py`

  **To merge / move:**
  - Any mode‑related scattered logic → `utils/trade_mode.py` + a small mode service.
  - Any DB‑direct calls from panels (`get_session`) → move into services:
    - Panel1 timeframe P&L logic → `services/stats_service.py`.

  ### 3.2 Duplicate Responsibilities

  **Balance management**
  - StateManager vs SimBalanceManager vs TradeManager vs Panel1.
    - Final: TradeManager (+Balance service) + StateManager only; UI just consumes.

  **Position tracking**
  - StateManager vs Panel2 vs PositionRepository vs JSON.
    - Final: `OpenPosition` + PositionRepository authoritative; StateManager metadata only; Panel2 view only.

  ### 3.3 JSON Storage to Eliminate

  - SIM balance JSON:
    - `data/sim_balance_{account}.json` (written by `core/sim_balance.py`).
    - Removed from runtime; optional one‑time migration.
  - Any position JSON files that duplicate DB state (old `state_SIM_.json`, `state_LIVE_*.json`):
    - Keep only Panel2’s timer‑only JSON (`runtime_state_panel2_{mode}_{account}.json`) if needed for UX; do not store
  position there.

  ### 3.4 Signals to Delete

  **From SignalBus (if not used):**
  - `orderRejected`
  - `marketTradeReceived`
  - `marketBidAskReceived`
  - `priceUpdated`
  - Any “Phase 4” placeholders not yet wired.

  **From Blinker (runtime):**
  - `signal_trade_account`
  - `signal_balance`
  - `signal_position`
  - `signal_order`

  ---

  ## 4. Resolve SIM/LIVE Balance Inconsistencies

  ### 4.1 Single Source of Truth

  - **SIM balance**:
    - Source: `TradeRecord` ledger (DB) + known starting balance (e.g. 10k).
    - View: `StateManager.sim_balance` maintained by services.
  - **LIVE balance**:
    - Source: DTC `AccountBalanceUpdate` (Type 600/602) reconciled with DB if necessary.
    - View: `StateManager.live_balance`.

  ### 4.2 JSON Strategy

  - Delete balance JSON from runtime (`sim_balance_{account}.json`) or mark it as deprecated tooling only.
  - Do **not** write new balance values to JSON during normal operation.

  ### 4.3 Unify DB + StateManager

  1. On app startup:
     - `MainWindow._setup_state_manager()` calls `state.load_sim_balance_from_trades()`.
     - This sets `state.sim_balance` and emits `balanceChanged`.
  2. On each SIM trade close:
     - `TradeCloseService`/`TradeManager` updates DB (`TradeRecord`) and computes new SIM balance:
       - `new_balance = state.get_balance_for_mode("SIM") + realized_pnl`.
       - `state.set_balance_for_mode("SIM", new_balance)` emits `balanceChanged`.
  3. On each LIVE balance update:
     - Balance service handles DTC `balanceUpdated` and updates `state.live_balance` via `set_balance_for_mode("LIVE",
  balance)`.

  ### 4.4 Where Balance Logic Lives

  - TradeManager/Balances service:
    - Knows how to adjust balances from P&L and what mode to use.
    - Writes trades and updates StateManager.
  - StateManager:
    - Knows the current SIM and LIVE balances and exposes `get_balance_for_mode`.
    - Emits `balanceChanged` when either changes.
  - Panel1:
    - Subscribes to StateManager (or SignalBus) and displays current balance; no extra logic.

  ### 4.5 Balance Reset Handling

  - Reset hotkey:
    - Should issue a *command* (e.g. `SignalBus.simBalanceResetRequested`) interpreted by a balance service.
    - Service sets `state.sim_balance = 10000.0`, records an audit event (e.g., `SimBalanceReset`), and emits
  `balanceChanged`.
    - Panel1 updates based on `balanceChanged`; no direct DB or JSON mutations.

  ### 4.6 Preventing Drift and Race Conditions

  - All balance changes go through a single service (TradeManager/BalanceService) and StateManager:
    - Use locks as currently done in `TradeManager._db_write_lock` and `StateManager._lock`.
    - No panel is allowed to mutate balances directly.
  - No fallback paths:
    - Remove Panel2’s legacy `TradeManager` fallback logic once the service is in place.

  ---

  ## 5. Refactor Trade Closure Pipeline

  ### 5.1 New Pipeline

  **Current (problematic)**
  Panel2 → PositionRepository (DB) → maybe TradeManager → Panel3/StateManager (partial).

  **Target**
  UI → Intent Signal → TradeCloseService → Repository + TradeManager → StateManager → Panels.

  ### 5.2 Components and Methods

  **New / Adjusted Signals**
  - In `core/signal_bus.py`:
    - `tradeCloseRequested = pyqtSignal(dict)`  # intent from UI
    - `positionClosed = pyqtSignal(dict)`       # canonical closed position view

  **TradeCloseService (new)**
  - Location: `services/trade_close_service.py` or inside `services/trade_service.py`.
  - Responsibilities:
    - Subscribe to `tradeCloseRequested`.
    - Determine mode/account from StateManager (`state.current_mode/current_account`) or from the trade dict, but
  validate consistency.
    - Call `PositionRepository.close_position(mode, account, exit_price, ...)`.
    - Compute new balances and call `state.set_balance_for_mode(mode, new_balance)`.
    - Emit `positionClosed(trade_view_dict)` and `tradeClosedForAnalytics(trade_view_dict)`.
    - Handle failures:
      - If repository returns `None` (no open position), log error and emit a failure event or status message via
  `SignalBus.errorMessagePosted`.

  **Panel2**
  - `notify_trade_closed(trade: dict)`:
    - Construct a trade payload with UI context (symbol, qty, entry/exit, account).
    - Emit `SignalBus.tradeCloseRequested(trade)`.
    - Do **not** call repositories or TradeManager directly.
  - Subscribe to `positionClosed`:
    - When a trade is closed, clear its local view state (e.g., `_position`, timers).

  **StateManager**
  - Provide `get_open_trade_mode()` and `has_active_position()` (already present).
  - When `positionClosed` arrives (from service), call `close_position()` to clear metadata.

  ### 5.3 Mode Detection Unification

  - TradeCloseService:
    - Uses StateManager’s `position_mode` or `current_mode` as the source for mode.
    - Uses `state.current_account` for account.
    - Optionally cross‑checks with trade payload’s `account` and logs any mismatch as an invariant violation.

  ### 5.4 Failure Propagation

  - TradeCloseService:
    - On failure (DB or state inconsistency):
      - Emits `SignalBus.errorMessagePosted("Failed to close position: reason")`.
      - Does not update balances or StateManager.
    - Panel2 can optionally listen for that error message to show a banner.

  ---

  ## 6. Clean Up Messaging

  ### 6.1 Dual Qt Signals and Mode Events

  **Problems**
  - DTC messages are emitted via both `message` and `messageReceived` and wired to the same handler.
  - Two `modeChanged` concepts: StateManager and SignalBus, but only StateManager’s is currently emitted.

  **Fix**
  1. In `core/app_manager.py::_connect_dtc_signals`:
     - Connect only one of `message` or `messageReceived` to `_on_dtc_message`.
     - The other remains for backward compatibility or is removed.
  2. Mode events:
     - Either:
       - Panels subscribe only to `StateManager.modeChanged`, and `SignalBus.modeChanged` is deleted, or
       - StateManager → small bridge → `SignalBus.modeChanged`, and panels subscribe only to the bus.
     - Choose one and remove the other to avoid confusion.

  ### 6.2 Blinker vs SignalBus

  **Problems**
  - Dual dispatch of the same events via Blinker and SignalBus.

  **Fix**
  - Remove Blinker from runtime per 2.6; keep only SignalBus.

  ### 6.3 Final Set of Allowed Events

  **From DTC adapter (SignalBus)**
  - `dtcConnected()`, `dtcDisconnected()`, `dtcSessionReady()`.
  - `tradeAccountReceived(dict)` – for account listing UI/services.
  - `balanceUpdated(balance: float, account: str)` – LIVE balance updates.
  - `positionUpdated(dict)` – raw position updates.
  - `orderUpdateReceived(dict)` – order/fill updates.

  **From Services**
  - `modeChanged(str)` (if bridged through SignalBus).
  - `positionOpened(object or dict)` – normalized position.
  - `positionClosed(dict)` – normalized closed trade/position view.
  - `tradeClosedForAnalytics(dict)` – for Panel3 analytics.
  - `metricsReloadRequested(str)` – from stats service when caches invalidate.

  **From UI / Panels**
  - `orderSubmitRequested(dict)` – user action.
  - `tradeCloseRequested(dict)` – user wants to close a position.
  - `modeSwitchRequested(str)` – user changes mode.
  - `timeframeChangeRequested(str)` – timeframe changes.
  - `themeChangeRequested()` – theme toggles.

  **Meta/UI**
  - `balanceDisplayRequested(float, str)` – app_manager hotkeys asking Panel1 to re‑display.
  - `equityPointRequested(float, str)` – add point to equity curve.
  - `statusMessagePosted(str, int)`, `errorMessagePosted(str)` – user notifications.

  ### 6.4 Enforcing “One Message = One Effect”

  - Design rule:
    - For each semantic event, pick **one** origin and **one** primary consumer responsibility.
  - Examples:
    - `balanceUpdated` (from DTC): consumed only by Balance service, which updates StateManager; panels do not listen
  directly.
    - `tradeCloseRequested` (from Panel2): consumed only by TradeCloseService.
    - `positionClosed`: consumed by Panel2 (UI), Panel3 (analytics), and maybe StateManager (for metadata), but none of
  these modify DB or balances; they are read‑only consumers of the result.

  ---

  ## 7. Dead Code Removal and Simplification Plan

  ### 7.1 Unused Signals

  **Delete or gate in `core/signal_bus.py`:**
  - Any signal without emitters/subscribers:
    - `orderRejected`
    - `marketTradeReceived`
    - `marketBidAskReceived`
    - `priceUpdated`
    - Others marked as “Phase 4” but never wired.

  ### 7.2 MessageRouter References

  **Remove from docs/tools where misleading for runtime:**
  - `APPSIERRA_FIXES.md` sections describing wiring MessageRouter.
  - `CORE_AUDIT.md`, `CODEBASE_ARCHITECTURE.md`, `DATA_SEPARATION_ARCHITECTURE.md` references to MessageRouter as if it
  were active.
  - `tools/router_diagnostic.py` – either delete or clearly mark as legacy.

  ### 7.3 Remove `wrap_blinker_signal`

  **File**: `core/signal_bus.py:280-325`.
  Action: delete the function and any related comments now that Blinker is no longer used in `_emit_app()`.

  ### 7.4 Remove Obsolete StateManager Generic Methods

  **File**: `core/state_manager.py:323-345`.
  Actions:
  - Remove `update_balance`, `update_position`, `record_order` and the `_state` dict used only for those generic
  trackers if not used elsewhere.
  - If any tests still rely on them for diagnostics, move that logic into a dedicated test helper instead.

  ### 7.5 Remove Panel Backups

  **Files:**
  - `panels/panel1_original_backup.py`
  - `panels/panel2_original_backup.py`
  - `panels/panel2_backup_before_extraction.py`
  - `panels/panel1.py.tmp`

  Action:
  - Delete once you’ve confirmed the new Panel1/Panel2 code is stable and covered by tests.

  ### 7.6 Remove Unused Helpers

  - Any helper in `utils/` or `tools/` that:
    - Is not imported anywhere in code or tests.
    - Exists only for the removed MessageRouter or Blinker routes.
    - Examples: router‑specific diagnostics, message trace scripts that assume MessageRouter.

  ---

  ## 8. “After Architecture” Blueprint

  ### 8.1 Final Architecture, Layered

  - **Integration / Adapter**
    - `DTCClientJSON` + DTC protocol modules.
  - **Domain Services**
    - Trade/Position/Balances services (including TradeClose).
    - Stats service.
    - Position recovery.
    - Mode resolver (could live in StateManager or a small service).
  - **State**
    - StateManager as the single in‑memory view: mode, balances, high‑level position metadata.
  - **UI**
    - Panels purely rendering and emitting user intents.
    - Widgets and dashboards as pure projections.

  ### 8.2 Final Event Pipeline

  **Inbound**
  DTC → `DTCClientJSON` → `_dtc_to_app_event` → `_emit_app` → SignalBus events.

  **Core processing**
  SignalBus → Domain services → DB + StateManager updates → SignalBus outcome events.

  **Outbound**
  StateManager + SignalBus → Panels → user view.

  ### 8.3 Final Persistence Rules

  - DB:
    - `OpenPosition` for open trades (single source of truth).
    - `TradeRecord` for closed trades and ledger.
  - JSON:
    - Only for non‑authoritative UI state (timers, layout) if kept.
    - No balances, no positions.
  - StateManager:
    - Mirror of DB/broker state; never long‑term storage.

  ### 8.4 Final Messaging System

  - Single runtime message bus: `SignalBus` (Qt signals).
  - No Blinker for production.
  - No MessageRouter.

  ### 8.5 Final Balance Flow

  **SIM**
  Trade close → TradeCloseService/TradeManager → DB (TradeRecord) → new SIM balance → StateManager → panels.

  **LIVE**
  DTC `AccountBalanceUpdate` → Balance service → StateManager → panels.

  ### 8.6 Final Position Lifecycle

  1. Entry:
     - DTC fill or user action → SignalBus `orderUpdateReceived` / `orderSubmitRequested`.
     - Position service opens/updates `OpenPosition` and notifies StateManager.
     - Emits `positionOpened` or `positionUpdated`.
     - Panel2/Panel3 update views.
  2. Exit:
     - User intent or DTC fill → `tradeCloseRequested` / `orderUpdateReceived`.
     - TradeCloseService closes `OpenPosition`, writes `TradeRecord`, updates balances.
     - Updates StateManager (position cleared, balance changed).
     - Emits `positionClosed` and `tradeClosedForAnalytics`.
     - Panels update views appropriately.

  ---

  ## 9. Refactor Order

  ### Step 1: Safety Fixes
  - Fix hard‑coded paths in Panel2.
  - Fix invalid `mgr.reset_balance()` call in `_on_reset_sim_balance_hotkey`.
  - Ensure `TradeManager.record_closed_trade()` updates balances reliably.

  ### Step 2: Remove Blocking Interference
  - Eliminate Blinker from runtime dispatch in `_emit_app()`.
  - Fix double‑fired DTC messages (`message` vs `messageReceived`).
  - Decide on single `modeChanged` pipeline and remove the other.

  ### Step 3: Remove Dead Code
  - Delete panel backups and MessageRouter‑dependent tools.
  - Remove `wrap_blinker_signal` and unused SignalBus signals.
  - Remove StateManager generic `update_balance`, `update_position`, `record_order` if unused.

  ### Step 4: Rebuild Persistence Boundaries
  - Declare DB `OpenPosition` and `TradeRecord` as authoritative state.
  - Ensure PositionRepository is the only writer to these tables.
  - Demote/remove JSON balance persistence; limit JSON to UI state.

  ### Step 5: Rebuild Event Pipeline
  - Make `SignalBus` the sole bus from DTC to services/panels.
  - Wire services to consume `balanceUpdated`, `positionUpdated`, `orderUpdateReceived`.
  - Implement mode resolution via StateManager and ModeResolver.

  ### Step 6: Rebuild Balance Service
  - Centralize SIM/LIVE balance mutation in TradeManager/Balance service.
  - Make StateManager the single balance cache.
  - Convert Panel1 to use only StateManager/statistics service for balances and P&L.

  ### Step 7: Rebuild Trade Lifecycle
  - Introduce `tradeCloseRequested` and `positionClosed` signals.
  - Implement TradeCloseService and remove Panel2’s direct repository/TradeManager calls.
  - Make Panel2 and Panel3 pure consumers of closure events.

  ### Step 8: Final Cleanup and Diagnostics
  - Update docs to reflect the new pipeline; remove MessageRouter/ Blinkers references from architecture docs.
  - Add targeted tests:
    - Trade closure pipeline (SIM and LIVE) adjusting balances correctly.
    - Mode isolation: SIM and LIVE never share positions/balances.
    - Event flow: each message type triggers exactly one set of side effects.