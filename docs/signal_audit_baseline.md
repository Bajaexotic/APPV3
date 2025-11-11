# Signal Audit Baseline Documentation

## Purpose

Before starting the architectural refactor to consolidate signal routing, we need a **baseline snapshot** of the current Blinker signal wiring.

## How to Run

**Prerequisites**: Must run in your virtual environment with all dependencies installed.

```bash
# Windows (from your machine):
cd C:\Users\cgrah\Desktop\APPSIERRA
.venv\Scripts\activate
python tools/signal_audit.py --verbose

# Optional: Export to CSV for analysis
python tools/signal_audit.py --verbose --csv
```

## Expected Baseline (BEFORE Refactoring)

Based on code analysis, we expect to see:

### signal_order

- **Receiver 1**: `core.app_manager.MainWindow._on_order` (line 224)
  - Location: app_manager.py:224-257
  - Purpose: Routes orders to Panel2, handles auto-mode detection, triggers balance refresh

### signal_position

- **Receiver 1**: `core.app_manager.MainWindow._on_position` (line 268)
  - Location: app_manager.py:268-293
  - Purpose: Routes positions to Panel2, handles auto-mode detection

### signal_balance

- **Receiver 1**: `core.app_manager.MainWindow._on_balance` (line 304)
  - Location: app_manager.py:304-317
  - Purpose: Routes balance to Panel1, marshals to Qt thread via QTimer.singleShot

### signal_trade_account

- **Receiver Count**: Likely 0 or 1
  - Currently may not have explicit handlers (trade account info used passively)

## Expected Issues (REDUNDANCY)

The audit will confirm these architectural issues:

1. **Dual Routing**:
   - Blinker signals → app_manager handlers → panels
   - MessageRouter exists but may not be fully utilized

2. **Duplicate Logic**:
   - Mode auto-detection appears in both `_on_order` and `_on_position` handlers
   - Balance refresh triggered from multiple locations

3. **Thread Safety Concerns**:
   - Qt thread marshaling done ad-hoc with `QTimer.singleShot(0, lambda: ...)`
   - Should be centralized in one helper

## Target State (AFTER Refactoring)

After completing Steps 2-4 of the refactor plan:

### All DTC Signals Should Show

- **Receiver Count**: Exactly 1
- **Receiver**: `core.message_router.MessageRouter.<handler_method>`
- **Location**: message_router.py

### No Receivers in

- `core.app_manager.MainWindow._on_order`
- `core.app_manager.MainWindow._on_position`
- `core.app_manager.MainWindow._on_balance`

## Running at App Startup (Optional)

To monitor signal wiring during development, add to `app_manager.py` or `main.py`:

```python
import os
if os.getenv("DEBUG_SIGNAL_AUDIT") == "1":
    from tools.signal_audit import audit_all_signals, print_audit_results
    results = audit_all_signals(verbose=True)
    print_audit_results(results, verbose=True)
```

Then run your app with:

```bash
DEBUG_SIGNAL_AUDIT=1 python main.py
```

## Pytest Integration

Run as a test to verify architectural invariants:

```bash
pytest tools/signal_audit.py::test_signal_audit -v
```

After refactoring, uncomment the assertions in `test_signal_audit()` to enforce:

- Each signal has at most 1 receiver
- All receivers are in MessageRouter (not app_manager)

## Next Steps

1. ✅ Signal audit tool created
2. ⬜ Run baseline audit (requires your local environment)
3. ⬜ Save baseline output to `logs/signal_audit_baseline.txt`
4. ⬜ Proceed with refactor Steps 2-4
5. ⬜ Re-run audit to verify changes
6. ⬜ Compare before/after to confirm consolidation

---

**Status**: Tool ready, awaiting baseline run on your local machine.
