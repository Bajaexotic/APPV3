# Balance Reset Issue - ROOT CAUSE FOUND

## The Problem

1. Trade closes → PnL updates balance to `$9,985.00` ✅
2. **Balance instantly resets back to `$10,000.00`** ❌

This happens because the DTC broker is overwriting your balance!

---

## Root Cause Identified

### Location: `core/message_router.py:242`

When a DTC AccountBalanceUpdate message (Type 600) arrives, the message router does this:

```python
def _on_balance_signal(self, sender, **kwargs) -> None:
    # Extract balance from DTC message
    balance_value = msg.get("balance") or msg.get("CashBalance") or msg.get("AccountValue")

    # OVERWRITE the balance in state manager!
    self.state.set_balance_for_mode(mode, float(balance_value))
```

**The Issue:**
- DTC sends the broker's **current account balance** (which doesn't know about your trades yet)
- Message router receives it and **overwrites** your updated balance
- Your PnL calculation is lost!

---

## The Flow (What's Happening Now)

```
1. Trade closes
   ├─ on_position_update() called
   ├─ record_closed_trade() called
   ├─ balance updated: $10,000 → $9,985
   ├─ [Balance shows $9,985] ✅ (momentarily visible)
   │
2. DTC Type 600 (AccountBalanceUpdate) arrives from broker
   ├─ message_router._on_balance_signal() called
   ├─ Extracts: balance_value = $10,000 (from broker)
   ├─ OVERWRITES: state.set_balance_for_mode(mode, 10000)
   │
3. [Balance resets to $10,000] ❌
```

---

## Why This Happens

The **DTC broker sends balance updates regularly**, including:
- After every trade execution
- After account activity
- Periodic updates

Each time, it sends the **broker's current balance**, which:
- ✓ Is accurate for the broker's records
- ✗ Doesn't include your local PnL calculations
- ✗ Overwrites your just-updated balance

---

## The Solution

We need to **prevent DTC balance messages from overwriting SIM mode balance updates**.

For **SIM mode**:
- ✗ Don't accept DTC balance updates (you're managing your own balance)
- ✓ Only use your calculated PnL to update balance

For **LIVE mode**:
- ✓ Accept DTC balance updates (broker is the source of truth)

---

## Implementation

The fix is simple - check the mode and skip DTC updates for SIM mode:

```python
def _on_balance_signal(self, sender, **kwargs) -> None:
    """Handle BALANCE_UPDATE Blinker signal."""

    # Extract mode first
    mode = detect_mode_from_account(account)

    # ⚠️  SKIP balance updates for SIM mode!
    if mode == "SIM":
        print(f"[SKIP] Ignoring DTC balance update for SIM mode")
        print(f"  (Using our calculated PnL balance instead)")
        return

    # Only update for LIVE mode
    if mode == "LIVE":
        self.state.set_balance_for_mode(mode, float(balance_value))
```

---

## What's Been Added

I've added comprehensive debug output to `message_router.py` so you can see when DTC is overwriting the balance:

```
[DEBUG MESSAGE_ROUTER] BALANCE_UPDATE signal received!
  Full message: {'balance': 10000.0, 'account': 'Sim1', ...}

[DEBUG MESSAGE_ROUTER] Extracted values:
  balance_value=10000.0
  account=Sim1

[DEBUG MESSAGE_ROUTER] Detected mode: SIM

[DEBUG MESSAGE_ROUTER] OVERWRITING balance!
  Old balance: $9,985.00
  New balance: $10,000.00
  ⚠️  This is from DTC and may overwrite your PnL update!
```

---

## Next Step: Fix Implementation

I need to implement the skip logic for SIM mode balance updates from DTC.

The fix requires:
1. Detecting mode BEFORE processing the balance
2. Skipping the update if mode == "SIM"
3. Allowing updates only for LIVE mode

Would you like me to implement this fix now?

---

## Why This Matters

Without this fix:
- ❌ PnL updates get overwritten by DTC
- ❌ Balance shows correct value momentarily, then resets
- ❌ No way to track cumulative P&L in SIM mode

With this fix:
- ✅ PnL updates persist (not overwritten)
- ✅ Balance updates from your calculations stick
- ✅ SIM mode properly tracks account growth/losses

---

## Summary

**Problem:** DTC AccountBalanceUpdate messages overwrite your PnL-updated balance

**Root Cause:** `message_router._on_balance_signal()` blindly updates balance for all modes

**Solution:** Skip DTC balance updates for SIM mode, use only PnL calculations

**Status:** Debug logging added, ready for fix implementation
