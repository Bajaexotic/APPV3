# SIM Mode Quick Start Guide

## What You Get

Your app now tracks SIM trading balance like a real account:

| Event | Balance |
|-------|---------|
| **Start** | $10,000 |
| **Win +$500** | $10,500 |
| **Lose -$200** | $10,300 |
| **Win +$1,000** | $11,300 |
| **Next Month** | Resets to $10,000 |

---

## Run Your App

```bash
cd C:\Users\cgrah\OneDrive\Desktop\APPSIERRA
python main.py
```

**Look for**:
- Panel 1 shows: **$10,000.00**
- Equity curve: Empty (no trades yet)

---

## Test It (3 Minutes)

### 1. Open a SIM Trade
- Entry price: 100
- Exit price: 105
- **Expected P&L**: +$500

### 2. Check Panel 1
```
Balance: $10,500.00 ✅
P&L: +$500.00 ✅
Equity Curve: 1 point added ✅
```

### 3. Close App & Reopen
```bash
# Close app
python main.py  # Reopen

# Expected: Balance still shows $10,500.00 ✅
```

### 4. Reset (Press Ctrl+Shift+R)
```
Dialog: "SIM balance reset to $10,000.00"
Panel 1: Shows $10,000.00 ✅
Ready for new strategy ✅
```

---

## Hotkeys

| Hotkey | What It Does |
|--------|--------------|
| **Ctrl+Shift+M** | Cycle modes: DEBUG → SIM → LIVE |
| **Ctrl+Shift+R** | Reset SIM balance to $10,000 |

---

## How It Works

### Automatic (You Do Nothing)
- ✅ Balance updates when trades close
- ✅ Balance persists when app closes/reopens
- ✅ Next month = auto-reset to $10K
- ✅ Equity curve shows all balance points
- ✅ Panel 3 shows only SIM trades

### Manual (You Press Keys)
- **Ctrl+Shift+R**: Reset balance to $10K mid-month

---

## Files Created

```
data/sim_balance.json
├─ Saves balance automatically
├─ Persists across app restarts
└─ Resets each calendar month
```

---

## Check Balance in Console

If you want to see the current balance:

```python
# Open Python console:
from core.app_state import get_state_manager
state = get_state_manager()
print(state.sim_balance)
```

Or check the file:
```bash
type data\sim_balance.json
```

---

## Troubleshooting

### Balance Not Updating?
1. Check you're in **SIM mode** (badge shows "SIM")
2. Make sure trade closes (status = filled)
3. Check logs:
   ```bash
   set DEBUG_DTC=1
   python main.py
   ```
4. Look for: `[SIM Balance] Adjusted by`

### Balance Wrong After Restart?
- Check if new month started (auto-reset)
- Check `data/sim_balance.json` exists
- If file corrupted, delete it (will recreate)

### Equity Curve Not Showing?
- Make sure you're in **SIM mode** (Ctrl+Shift+M)
- Make at least one trade
- Close and reopen app

---

## That's It!

Your SIM balance now works like a real trading account. Start making trades and watch your balance update automatically.

**Key Points**:
- ✅ Automatic P&L tracking
- ✅ Persistent across restarts
- ✅ Monthly auto-reset to $10K
- ✅ Manual reset: Ctrl+Shift+R
- ✅ Complete trade history in Panel 3

**Happy trading! 🚀**

