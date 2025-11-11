# PNL DEBUGGING FINDINGS

## Database State
- **Total trades**: 48
- **Trades with NULL PnL**: 25 (52%)
- **Trades with valid PnL**: 23 (48%)
- **Total calculated PnL**: $-83.75

## Root Cause: Duplicate Entry Records

When a position closes, trades are being recorded with:
- **entry_price = exit_price** (breakeven)
- **realized_pnl = NULL**

Example:
```
ID=47: Entry=$6839.25, Exit=$6839.25, PnL=NULL
ID=43: Entry=$6843.0, Exit=$6843.0, PnL=NULL
ID=42: Entry=$6843.0, Exit=$6843.0, PnL=NULL
ID=41: Entry=$6843.0, Exit=$6843.0, PnL=NULL
```

These are the **duplicate records from the old bug** where `on_position_update()` called `record_closed_trade()` without an exit price.

## Why Panel 3 Shows $0.00

When Panel 3 queries trades for a timeframe:
1. It gets trades with NULL and valid PnL
2. When summing: NULL values might be treated as 0
3. Or database query doesn't filter NULL values properly
4. Result: $0.00 instead of actual $-83.75

## Impact on Panel 1 (Session PnL)

Currently Panel 1 uses "session start balance" (when app opened) as the baseline.
Should be using actual timeframe-based calculations:
- **LIVE**: Last 1 hour
- **1D**: Last day (midnight-midnight)
- **1W**: Last 7 days
- **1M**: Last 30 days
- **3M**: Last 90 days
- **YTD**: Jan 1 to now

## What Needs to be Fixed

### 1. Clean Up Database (URGENT)
Delete or fix the 25 duplicate NULL-PnL records:
```sql
DELETE FROM trade WHERE realized_pnl IS NULL;
```

Or update them with proper PnL calculation:
```sql
UPDATE trade
SET realized_pnl = (exit_price - entry_price) * qty
WHERE realized_pnl IS NULL AND exit_price IS NOT NULL;
```

### 2. Panel 3 (Stats Display)
- Filter out NULL PnL records in stats_service.py
- Sum only valid PnL trades
- Display: `$-83.75` (or correct amount)

### 3. Panel 1 (Session PnL)
- Replace "session start balance" with actual timeframe PnL
- For LIVE: Sum trades from last 1 hour
- For 1D: Sum trades from last 24 hours
- For 1W: Sum trades from last 7 days
- Etc.
- Display in format: `[DOWN ICON] RED FONT $83.75 (0.84%)`

### 4. stats_service.py
- Remove unicode check marks that cause crashes
- Fix to handle NULL PnL values properly
- Add debug output that works on Windows console

### 5. Future Prevention
- In record_closed_trade(): Only record if realized_pnl is NOT NULL
- Check: if entry_price == exit_price, skip recording
- Or only call from Panel2 (already fixed), never from on_position_update()

## Quick Actions

1. **Immediate**: Delete NULL PnL trades from database
   ```python
   from data.db_engine import get_session
   from data.schema import TradeRecord

   with get_session() as s:
       s.query(TradeRecord).filter(TradeRecord.realized_pnl.is_(None)).delete()
       s.commit()
       print("Deleted NULL PnL trades")
   ```

2. **Update Panel 3 stats_service.py**:
   - Filter: `realized_pnl is not None`
   - Remove unicode characters

3. **Update Panel 1 _update_pnl_for_current_tf()**:
   - Query trades for actual timeframe
   - Calculate PnL from timeframe start
   - Display with proper formatting

## Testing

After fixes:
1. Database: Should show 23 valid trades with $-83.75 total
2. Panel 3: Should show $-83.75 for appropriate timeframe
3. Panel 1 LIVE: Should show PnL for last 1 hour
4. Panel 1 1D: Should show PnL for last 24 hours
5. Close and reopen: Balance should persist correctly
