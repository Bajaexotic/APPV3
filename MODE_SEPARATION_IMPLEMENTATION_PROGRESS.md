# Mode Separation Architecture - Implementation Progress

**Date**: 2025-11-11
**Branch**: `claude/implement-mode-separation-architecture-011CV2nGza51j22C11QgkKm6`
**Status**: Phase 1 Complete, Phase 2 In Progress

---

## Phase 1: Foundational Utilities ✅ COMPLETE

### 1. Atomic Persistence (`utils/atomic_persistence.py`) ✅
**Status**: Complete and tested

Features implemented:
- ✅ `save_json_atomic()` - Atomic writes using temp → rename
- ✅ `load_json_atomic()` - Load with schema validation
- ✅ `get_scoped_path()` - Generate (mode, account)-scoped paths
- ✅ `get_utc_timestamp()` - UTC-only timestamps
- ✅ Schema versioning (v2.0) in all files

### 2. Account-Scoped SIM Balance (`core/sim_balance.py`) ✅
**Status**: Complete with breaking changes

**BREAKING CHANGES**:
- All functions now require `account` parameter
- Old: `get_sim_balance()` → New: `get_sim_balance(account)`
- Storage: `data/sim_balance_{account}.json` (one file per account)

Features implemented:
- ✅ Separate balance tracking per SIM account (Sim1, Sim2, etc.)
- ✅ Ledger-based balance (starting_balance + realized_pnl - fees)
- ✅ Lazy loading with in-memory cache
- ✅ Atomic persistence for all balance updates
- ✅ Account list tracking

**Migration Notes**:
- Any code calling `get_sim_balance()` must be updated to pass account
- Old `data/sim_balance.json` will be ignored (create new per-account files)

### 3. Debounce Logic (`utils/trade_mode.py`) ✅
**Status**: Complete

Features implemented:
- ✅ 750ms debounce window (configurable)
- ✅ Requires 2 consecutive agreeing signals
- ✅ `should_switch_mode_debounced()` function
- ✅ `reset_debounce()` for manual resets
- ✅ Mode and account agreement checking

### 4. Provisional Boot Mode (`utils/provisional_mode.py`) ✅
**Status**: Complete

Features implemented:
- ✅ Save/load last known (mode, account)
- ✅ 24-hour TTL
- ✅ `save_last_known_mode()` - Persist on mode change
- ✅ `load_last_known_mode()` - Load with TTL check
- ✅ `get_provisional_mode_status()` - Detailed status
- ✅ Storage: `data/last_known_mode.json`

---

## Phase 2: Core Component Updates 🚧 PENDING

### 5. State Manager Mode History (`core/state_manager.py`) ⏳
**Status**: Pending

Planned changes:
- [ ] Add `mode_history: list[tuple[datetime, str, str]]` attribute
- [ ] Track all mode changes with UTC timestamps
- [ ] Add `get_mode_history()` method
- [ ] Add `get_last_mode_change()` method
- [ ] Integrate with provisional boot mode

### 6. Panel1 (mode, account) Scoping (`panels/panel1.py`) ⏳
**Status**: Pending - Current implementation has SIM/LIVE separation but not account-scoped

Current state:
- Has `_equity_points_sim` and `_equity_points_live` (mode-separated)
- Missing: Account scoping within each mode

Required changes:
- [ ] Replace lists with dicts: `_equity_curves: dict[tuple[str, str], list]`
- [ ] Add `current_account: Optional[str]` attribute
- [ ] Update `set_trading_mode(mode, account)` signature
- [ ] Update `update_equity_series_from_balance()` to use scoped curves
- [ ] Add `_get_equity_curve(mode, account)` helper
- [ ] Integrate with provisional boot mode on startup

### 7. Panel2 (mode, account) Scoping (`panels/panel2.py`) ⏳
**Status**: Pending - Current implementation has global STATE_PATH

Current state:
- Has `STATE_PATH` constant (not scoped)
- Has `_load_state()` and `_save_state()` (currently disabled)

Required changes:
- [ ] Remove hardcoded `STATE_PATH` constant
- [ ] Add `current_mode: str` and `current_account: str` attributes
- [ ] Add `_get_state_path()` method using `get_scoped_path()`
- [ ] Update `set_trading_mode(mode, account)` signature
- [ ] Re-enable `_load_state()` and `_save_state()` with atomic writes
- [ ] Call `_save_state()` on position updates
- [ ] Call `_load_state()` on mode change

### 8. Message Router Recovery Sequence (`core/message_router.py`) ⏳
**Status**: Pending

Required changes:
- [ ] Add `_recovery_sequence()` async method
- [ ] Implement 3-step pull:
  1. Request positions now (DTC Type 500)
  2. Request open orders now (DTC Type 300)
  3. Request fills since last seen (DTC Type 303)
- [ ] Add `_get_last_seen_timestamp_utc()` helper
- [ ] Add `_relink_brackets()` for OCO relationships
- [ ] Call recovery on reconnect/startup

### 9. Mode Drift Sentinel (`core/message_router.py`) ⏳
**Status**: Pending

Required changes:
- [ ] Add `_check_mode_drift(msg)` method
- [ ] Compare incoming `TradeAccount` with active `(mode, account)`
- [ ] Log structured event on mismatch (non-blocking)
- [ ] Show yellow banner in UI (optional)
- [ ] Add mode drift to status bar

### 10. Coalesced UI Updates (`core/message_router.py`) ⏳
**Status**: Pending

Required changes:
- [ ] Add `_ui_refresh_pending: bool` flag
- [ ] Add `_schedule_ui_refresh()` method
- [ ] Add `_flush_ui_updates()` method
- [ ] Set `UI_REFRESH_INTERVAL_MS = 100` (10 Hz)
- [ ] Call `_schedule_ui_refresh()` instead of immediate `update()`
- [ ] Use `QTimer.singleShot()` for coalescing

---

## Phase 3: LIVE Arming Gate 🚧 PENDING

### 11. LIVE Arming Gate (`config/settings.py` + UI) ⏳
**Status**: Pending

Required changes:
- [ ] Add `LIVE_ARMED: bool = False` to settings
- [ ] Add `arm_live_trading()` function
- [ ] Add `disarm_live_trading()` function
- [ ] Auto-disarm on: disconnect, config reload, mode drift
- [ ] Add "Arm LIVE" button to UI
- [ ] Add red glow effect when armed
- [ ] Block LIVE orders when not armed

---

## Testing & Validation 🚧 PENDING

### 12. Test Suite ⏳
**Status**: Pending

Required tests:
- [ ] Unit tests for atomic_persistence
- [ ] Unit tests for sim_balance (account-scoped)
- [ ] Unit tests for debounce logic
- [ ] Unit tests for provisional boot mode
- [ ] Integration test: mode switching with debounce
- [ ] Integration test: (mode, account) scoping in panels
- [ ] Integration test: recovery sequence after disconnect
- [ ] Manual test: LIVE arming gate

### 13. Documentation Updates ⏳
**Status**: Pending

Required docs:
- [ ] Update README with breaking changes
- [ ] Migration guide for sim_balance API changes
- [ ] Example usage for new utilities
- [ ] Update developer guide

---

## Summary

### Commits So Far
1. **8aa0f1e** - Add comprehensive mode separation architecture documentation
2. **31f2533** - Phase 1: Add foundational utilities for mode separation architecture

### Files Created
- `utils/atomic_persistence.py` (217 lines)
- `utils/provisional_mode.py` (146 lines)
- `DATA_SEPARATION_ARCHITECTURE.md` (1041 lines)
- `MODE_SEPARATION_IMPLEMENTATION_PROGRESS.md` (this file)

### Files Modified
- `core/sim_balance.py` - Account-scoped balance (BREAKING)
- `utils/trade_mode.py` - Added debounce logic

### Breaking Changes
⚠️ **core/sim_balance.py**: All functions now require `account` parameter

**Old code**:
```python
balance = get_sim_balance()
set_sim_balance(12000.0)
```

**New code**:
```python
balance = get_sim_balance("Sim1")
set_sim_balance("Sim1", 12000.0)
```

### Next Steps (Phase 2)
1. Add mode history to state_manager
2. Update Panel1 for (mode, account) scoping
3. Update Panel2 for (mode, account) scoping
4. Implement recovery sequence in message_router
5. Add mode drift sentinel
6. Add coalesced UI updates

**Estimated Remaining Work**: 6-8 hours for Phase 2 + testing

---

## Notes

- All new code uses UTC timestamps exclusively
- All persistence uses atomic writes (temp → rename)
- Schema version 2.0 for all new files
- Debounce prevents mode flickering
- Provisional boot handles stale state gracefully

**Status**: Ready for Phase 2 implementation
**Next Task**: Add mode history tracking to state_manager
