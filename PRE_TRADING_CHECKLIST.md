# PRE-TRADING CHECKLIST

Use this checklist before starting your trading day.

---

## 5-Minute Setup Check

### 1. Verify Database Configuration
```bash
python tools/database_setup.py --check
```

**Expected Output:**
```
✓ Config Valid
✓ Connected
✓ Tables Exist
```

**If any check fails**: Run `python tools/database_setup.py --init` to fix

### 2. Test SIM Mode
1. Open APPSIERRA
2. Ensure mode badge shows "SIM"
3. Execute a test trade: entry 100, exit 105
4. Verify Panel 1 shows updated balance
5. Verify Panel 3 shows 1 trade, +$500 PnL

### 3. Test App Restart
1. Close APPSIERRA completely
2. Reopen APPSIERRA
3. Verify Panel 1 balance is unchanged
4. Verify Panel 3 still shows the test trade
5. If both correct → Everything works ✓

---

## Pre-Trading Verification (Choose Your Trading Mode)

### If Trading in SIM Mode

- [x] Mode badge shows "SIM"
- [x] Balance is correct (should be $10,000 or updated balance)
- [x] Panel 3 shows your historical SIM trades
- [x] No LIVE trades visible in Panel 3
- [x] Ready to trade ✓

### If Trading in LIVE Mode

- [x] Mode badge shows "LIVE"
- [x] Account field shows correct account number (e.g., "120005")
- [x] Balance is correct for LIVE account
- [x] Panel 3 shows only LIVE trades (no SIM trades)
- [x] Ready to trade ✓

### If Switching Between SIM and LIVE

1. Execute trade in Mode A
2. Switch to Mode B (Ctrl+Shift+M)
3. Check Panel 3 updates correctly
4. Mode A trades disappear from Panel 3
5. Mode B trades appear in Panel 3
6. Ready to switch ✓

---

## Optional: Full Diagnostics (Before Important Trading)

```bash
# Generate complete persistence report
python tools/persistence_monitor.py --report
```

**Report includes:**
- Database status
- Trade count by mode
- Balance verification
- Performance metrics
- Error logs

---

## Quick Troubleshooting

### Problem: Panel 3 shows no trades
**Solution 1**: Check if trades exist for current timeframe (try "YTD")
**Solution 2**: Check if mode matches trade mode (SIM trades don't show in LIVE mode)
**Solution 3**: Run `python tools/database_setup.py --check`

### Problem: Balance doesn't update
**Solution 1**: Close the trade properly (qty must go to 0)
**Solution 2**: Check Panel 1 refreshes (may be cached)
**Solution 3**: Restart app to reload balance

### Problem: Can't switch modes
**Solution 1**: Press Ctrl+Shift+M to toggle mode
**Solution 2**: Close any open trades first
**Solution 3**: Check Terminal for error messages

### Problem: App won't start
**Solution 1**: Run `python tools/database_setup.py --init`
**Solution 2**: Delete `data/appsierra.db` and restart app
**Solution 3**: Check Python version is 3.8+

---

## Production Safeguards (Already Implemented)

✅ **Database Fallback Chain**
- PostgreSQL → SQLite → In-Memory
- App never crashes due to database issues

✅ **Mode Isolation**
- SIM and LIVE trades completely separate
- No accidental data mixing

✅ **Balance Persistence**
- Survives app restart
- Monthly auto-reset to $10,000

✅ **Error Handling**
- All critical operations wrapped in try/catch
- Graceful degradation if anything fails

✅ **Data Validation**
- Empty state handling (no crashes on empty results)
- Automatic type conversion
- Missing field defaults

---

## What to Do Before Your First LIVE Trade

1. **Verify Setup** (1 minute)
   ```bash
   python tools/database_setup.py --check
   ```

2. **Test SIM Mode** (5 minutes)
   - Close a test SIM trade
   - Verify Panel 1 balance updates
   - Restart app
   - Verify balance persists

3. **Read Documentation** (5 minutes)
   - Skim: `QUICK_PERSISTENCE_REFERENCE.md`
   - This answers all common questions

4. **Start LIVE Trading** ✓
   - You're ready!

---

## During Trading

### Keep Eye On

- **Panel 1**: Current balance (updates on trade close)
- **Panel 2**: Open positions and current P&L
- **Panel 3**: Statistics for your trading mode
- **Mode Badge**: Confirm you're in correct mode

### Automatic Features (No Action Needed)

- ✓ Balance updates automatically
- ✓ Trades persist automatically
- ✓ Statistics compute automatically
- ✓ Mode isolation happens automatically

### If Something Looks Wrong

1. Check mode badge (Panel 1, top-right)
2. Check timeframe in Panel 3 (default "1D")
3. Run diagnostics: `python tools/database_setup.py --check`
4. Restart app if needed
5. All data will be recovered from database

---

## End of Trading Day

### Optional: Generate Report
```bash
python tools/persistence_monitor.py --report
```

### Optional: Monitor Real-Time
```bash
python tools/persistence_monitor.py --watch
```

### Before Next Trading Day
- Same checklist, repeat step 1

---

## Key Numbers to Remember

- **SIM Starting Balance**: $10,000 (auto-resets monthly)
- **SIM Max Leverage**: 4:1 (standard)
- **Mode Switch**: Ctrl+Shift+M
- **Balance Reset**: Ctrl+Shift+R (SIM only)
- **Statistics Timeframes**: 1D, 1W, 1M, 3M, YTD

---

## Emergency Recovery

### If Database Gets Corrupted

```bash
# This will:
# 1. Backup old database
# 2. Create new schema
# 3. Verify everything works

python tools/database_setup.py --init
```

### If You Lose Balance

1. Check `data/sim_balance.json` for backup
2. Check database for trade history
3. Run: `python tools/persistence_monitor.py --report`
4. Balance can be manually adjusted in config if needed

### If App Won't Start

1. Delete `data/appsierra.db`
2. Delete `data/sim_balance.json`
3. Restart app (will recreate both)
4. Run: `python tools/database_setup.py --init`

---

## Support

All questions answered in:
- `QUICK_PERSISTENCE_REFERENCE.md` - Fast answers
- `PERSISTENCE_ARCHITECTURE.md` - Technical details
- `PANEL3_MODE_VERIFICATION.md` - Mode-specific help

---

## You're Ready! ✓

Everything is set up correctly and verified.

Start trading with confidence. Your data is safe.

**Happy trading!** 🚀
