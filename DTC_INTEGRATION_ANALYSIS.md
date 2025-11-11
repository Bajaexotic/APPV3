# DTC Protocol Integration Analysis - APPSIERRA

**Date**: November 5, 2025  
**Thoroughness Level**: Very Thorough  
**Status**: Partially Implemented - Missing Critical Trading Features

---

## EXECUTIVE SUMMARY

The APPSIERRA codebase has a **partially implemented DTC integration** with the following capabilities:

### What Works ✓

- TCP connection management with auto-reconnect
- DTC heartbeat and keepalive system
- Account information retrieval
- Position tracking and updates
- Order status monitoring and fills
- Historical trade persistence and statistics
- Market data reception (bid/ask, trades)
- Account balance tracking

### What's Missing (CRITICAL) ✗

- **ORDER SUBMISSION** - Cannot place new trades
- **ORDER CANCELLATION** - Cannot exit trades with cancel requests
- **ORDER MODIFICATION** - Cannot adjust order prices/quantities
- **Symbol Lookup** - No security definition retrieval
- **Complete State Management** - StateManager has incomplete implementations
- **Session Market Data** - Session High/Low/Volume/OpenInterest not dispatched

---

## 1. DTC MESSAGE TYPES CURRENTLY HANDLED

### Connection & Session (Types 1-6)

- ✓ LogonRequest/Response (1-2)
- ✓ Heartbeat (3)
- Logoff (4) - defined
- EncodingRequest/Response (5-6) - handled but not fully utilized

### Market Data (Types 101-124)

- ◐ MarketDataRequest (101) - partially working
- MarketDataReject (103) - NOT dispatched
- ✓ MarketDataUpdateTrade (107) - working
- ✓ MarketDataUpdateBidAsk (108) - working
- ✗ MarketDataUpdate Session\* (120-124) - NOT dispatched

### Order Management (Types 300-313)

- ✗ **SubmitNewSingleOrder (300)** - DEFINED BUT NOT IMPLEMENTED
- ✓ OrderUpdate (301) - working
- HistoricalOrderFillsRequest (303) - working
- ✓ HistoricalOrderFillResponse (304) - working
- ✓ OpenOrdersRequest (305) - working
- ✓ PositionUpdate (306) - working
- ✓ OrderFillResponse (307) - working
- ✗ **OrderCancelRequest (309)** - DEFINED BUT NOT IMPLEMENTED
- ✗ **OrderCancelReplaceRequest (310)** - DEFINED BUT NOT IMPLEMENTED
- OrderCancelReject (311) - NOT dispatched
- OrderReject (312) - NOT dispatched
- OrdersCancelledNotification (313) - NOT dispatched

### Accounts (Types 400-401, 500, 600-601)

- ✓ TradeAccountsRequest (400) / TradeAccountResponse (401)
- ✓ CurrentPositionsRequest (500)
- ✓ AccountBalanceUpdate (600)
- ✓ AccountBalanceRequest (601)

### Historical Data (Types 700-704)

- ✗ HistoricalPriceData\* (700-703) - TYPES NOT DISPATCHED
- HistoricalPriceDataReject (704) - NOT dispatched

### Miscellaneous (Types 800-802)

- UserMessage (800) - NOT dispatched
- GeneralLogMessage (801) - NOT dispatched
- AlertMessage (802) - NOT dispatched

---

## 2. MESSAGE TYPES SUBSCRIBED ON STARTUP

**Location**: `services/dtc_json_client.py::probe_server()` (lines 453-515)

### Startup Sequence

1. **Trade Accounts Request** → Gets available accounts
2. **Current Positions Request** → Seeds positions (with seeding completion detection)
3. **Open Orders Request** → Seeds open orders (with seeding completion detection)
4. **Historical Fills Request** → Loads 30-day trade history (CRITICAL for Panel 3)
5. **Account Balance Request** → Gets current balance
6. **Market Data Subscription** (OPTIONAL) → Only if SIERRA_MD_SYMBOL env var set

### Seeding Logic

- Positions complete when: `TotalNumberMessages == MessageNumber` OR `NoPositions=1`
- Orders complete when: `TotalNumberMessages == MessageNumber` OR `NoOrders=1`
- Callbacks: `on_positions_seed_done()` and `on_orders_seed_done()`

**Key Issue**: Market data NOT subscribed by default - only if env var configured

---

## 3. UI PANELS AND DATA REQUIREMENTS

### Panel 1: Balance & Investing (panels/panel1.py)

**Purpose**: Account balance display, equity curve visualization, timeframe selection

**Data Sources**:

- DTC: TradeAccountResponse, AccountBalanceUpdate
- CSV: snapshot.csv (last price, session H/L, VWAP, CumDelta)
- Database: Trade records for equity curve calculation

**Required Data**:

- Account name and balance
- Market price (for unrealized P&L)
- Equity timeseries by timestamp

**Components**:

- Connection status icon
- Timeframe pills (LIVE, 1D, 1W, 1M, 3M, YTD)
- Equity curve graph with pyqtgraph
- Theme-aware styling

---

### Panel 2: Live Trading (panels/panel2.py)

**Purpose**: Real-time trade monitoring with heat timer and live P&L

**Data Sources**:

- DTC: PositionUpdate, OrderUpdate, OrderFillResponse
- CSV: snapshot.csv
- Local state: entry_price, qty, side, stop_price, target_price

**Tracked Metrics**:

- Unrealized P&L (with flashing warning at thresholds)
- Duration in trade
- "Heat" duration (since max drawdown)
- Per-trade MAE/MFE extremes
- Session high/low during trade

**Handlers**:

- `on_position_update(payload)` - Updates position context
- `on_order_update(payload)` - Detects fills and closes trades
- `notify_trade_closed()` - Persists closed trade and emits signal

**Components**:

- Timeframe pills with active highlighting
- 3×5 metric grid (15 metrics)
- Flash timer for warning states
- Trade persistence to database

---

### Panel 3: Trading Statistics (panels/panel3.py)

**Purpose**: Historical performance metrics and trade analysis

**Data Sources**:

- Database: TradeRecord filtered by exit_time within timeframe
- DTC: HistoricalOrderFillResponse (initial load)

**Computed Metrics** (18 total):

```
Total PnL, Max Drawdown, Max Run-Up, Expectancy, Avg Time In Trade,
Trade Count, Best Trade, Worst Trade, Hit Rate, Commissions Total,
Avg R per Trade, Profit Factor, Win/Loss Streak, MAE, MFE,
Sharpe Ratio, EQ Slope*, Std Dev*
```

(\* = marked as implemented but needs verification)

**Timeframes**: 1D, 1W, 1M, 3M, YTD (plus option for static filtering)

**Components**:

- Title with centering
- Timeframe pills with color sync to PnL direction
- 5-column metric grid
- Sharpe ratio bar widget

---

## 4. CRITICAL GAPS IN DTC FUNCTIONALITY

### 1. ORDER SUBMISSION ✗ CRITICAL

**Status**: Type 300 defined but NO implementation exists

**Missing**:

- No `submit_order()` method in DTCClientJSON or data_bridge
- No order validation logic
- No UI button/dialog to place orders
- No confirmation workflow
- No order type/TIF defaults

**Required Implementation**:

```python
def submit_order(self, symbol, qty, side, price1,
                 order_type="Limit", tif="Day", trade_account=None):
    msg = {
        "Type": 300,  # SUBMIT_NEW_SINGLE_ORDER
        "RequestID": self._next_req_id(),
        "Symbol": symbol,
        "BuySell": side,  # "Buy" or "Sell"
        "Quantity": int(qty),
        "Price1": float(price1),
        "OrderType": order_type,  # "Limit", "Market", "Stop", "StopLimit"
        "TimeInForce": tif,  # "Day", "GTC", "IOC", "FOK", "OPG"
    }
    if trade_account:
        msg["TradeAccount"] = trade_account
    self.send(msg)
```

**Impact**: Cannot place trades from application

---

### 2. ORDER CANCELLATION ✗ CRITICAL

**Status**: Type 309 defined but NO implementation exists

**Missing**:

- No `cancel_order()` method
- No way to cancel by ServerOrderID or ClientOrderID
- No batch cancel capability
- No cancel confirmation
- No UI for cancellation

**Required Implementation**:

```python
def cancel_order(self, server_order_id, trade_account=None):
    msg = {
        "Type": 309,  # ORDER_CANCEL_REQUEST
        "RequestID": self._next_req_id(),
        "ServerOrderID": server_order_id,
    }
    if trade_account:
        msg["TradeAccount"] = trade_account
    self.send(msg)
```

**Current Workaround**: Trades only exit through fill detection in Panel2

**Impact**: Cannot exit positions using cancel requests

---

### 3. ORDER MODIFICATION ✗ CRITICAL

**Status**: Type 310 defined but NO implementation exists

**Missing**:

- No `modify_order()` method
- No price/quantity adjustment capability
- No UI for modification
- No confirmation workflow

**Required Implementation**:

```python
def modify_order(self, server_order_id, new_qty=None, new_price=None,
                new_price2=None, trade_account=None):
    msg = {
        "Type": 310,  # ORDER_CANCEL_REPLACE_REQUEST
        "RequestID": self._next_req_id(),
        "ServerOrderID": server_order_id,
    }
    if new_qty is not None:
        msg["Quantity"] = int(new_qty)
    if new_price is not None:
        msg["Price1"] = float(new_price)
    if new_price2 is not None:
        msg["Price2"] = float(new_price2)
    if trade_account:
        msg["TradeAccount"] = trade_account
    self.send(msg)
```

**Impact**: Cannot adjust existing orders

---

### 4. SECURITY DEFINITIONS / SYMBOL LOOKUP ◐ PARTIAL

**Status**: Partially implemented but incomplete

**What Exists**:

- `subscribe_symbol(symbol, exchange)` method (dtc_json_client.py:539)
- Sends SecurityDefinitionForSymbolRequest
- Handler for SecurityDefinitionResponse (dispatches to `on_security_definition`)

**What's Missing**:

- No symbol search interface
- No contract spec display (multiplier, tick size, hours, exchange)
- on_security_definition callback never wired to UI
- No symbol validation before order submission
- No contract picker for symbol variants

**Required for Completion**:

1. Symbol lookup dialog with search
2. Display contract specifications (multiplier, min price, tick size)
3. Wire security definition responses to UI panel
4. Validate symbols before allowing order submission

---

### 5. STATE MANAGER INCOMPLETE METHODS ✗ BROKEN

**Status**: Methods called but not implemented

**Problem**: `core/message_router.py` calls these methods but they don't exist:

```python
# Line 105: called but not implemented
self.state.update_balance(bal)

# Line 118: called but not implemented
self.state.update_position(sym, qty, avg)

# Line 128: called but not implemented
self.state.record_order(payload)
```

**Current Implementation** (`core/state_manager.py`):

- Only `set()`, `get()`, `delete()`, `dump()`, `update()` exist (generic key-value)
- No balance tracking
- No position tracking
- No order recording

**Impact**: State not properly persisted; router calls fail silently

**Solution**: Implement these methods in StateManager:

```python
def update_balance(self, balance):
    self._state["balance"] = balance

def update_position(self, symbol, qty, avg_price):
    positions = self._state.get("positions", {})
    if qty == 0:
        positions.pop(symbol, None)
    else:
        positions[symbol] = {"qty": qty, "avg_price": avg_price}
    self._state["positions"] = positions

def record_order(self, payload):
    orders = self._state.get("orders", [])
    orders.append(payload)
    self._state["orders"] = orders
```

---

### 6. HISTORICAL PRICE DATA ✗ NOT IMPLEMENTED

**Status**: Message types 700-704 defined but no dispatchers

**Missing**:

- HistoricalPriceDataResponseHeader (701) - NOT dispatched
- HistoricalPriceDataRecordResponse (702) - NOT dispatched
- HistoricalPriceDataTickRecordResponse (703) - NOT dispatched
- HistoricalPriceDataReject (704) - NOT dispatched

**Impact**: Cannot fetch candlestick or tick data

---

### 7. ORDER REJECTION HANDLING ✗ NOT IMPLEMENTED

**Status**: Message types defined but no dispatchers

**Missing**:

- OrderReject (312) - NOT dispatched
- OrderCancelReject (311) - NOT dispatched
- No UI notification of rejections
- Silent failures if orders are rejected

**Impact**: Users unaware of order rejections

---

### 8. MARKET DATA SESSION UPDATES ✗ NOT DISPATCHED

**Status**: Types 120-124 received but not handled

**Missing**:

- MarketDataUpdateSessionOpen (120) - NOT dispatched
- MarketDataUpdateSessionHigh (121) - NOT dispatched
- MarketDataUpdateSessionLow (122) - NOT dispatched
- MarketDataUpdateSessionVolume (123) - NOT dispatched
- MarketDataUpdateOpenInterest (124) - NOT dispatched

**Impact**: Session stats unavailable from market data

---

## 5. MARKET DATA SUBSCRIPTION STATUS

**Verdict**: Partially working, missing dynamic subscription

### What Works ✓

1. Startup market data request (if SIERRA_MD_SYMBOL env set)
2. MarketDataUpdateTrade (107) dispatch to on_md_trade
3. MarketDataUpdateBidAsk (108) dispatch to on_md_bidask
4. CSV fallback (snapshot.csv with last/H/L/VWAP/CumDelta)

### What's Missing ✗

1. **No default subscription** - only if env var set
2. **No dynamic subscription** - can't change symbols at runtime
3. **No unsubscribe** - can't stop receiving updates
4. **No rejection handling** - MarketDataReject (103) not dispatched
5. **No session updates** - Types 120-124 not dispatched

### Recommendation

Add these methods to DTCClientJSON:

```python
def subscribe_market_data(self, symbol, exchange=""):
    """Subscribe to live market data for symbol"""
    self.send({
        "Type": 101,  # MARKET_DATA_REQUEST
        "RequestID": self._next_req_id(),
        "RequestAction": 1,  # 1 = Subscribe
        "Symbol": symbol,
        "Exchange": exchange,
    })

def unsubscribe_market_data(self, symbol_id):
    """Unsubscribe from market data"""
    self.send({
        "Type": 101,
        "RequestID": self._next_req_id(),
        "RequestAction": 2,  # 2 = Unsubscribe
        "SymbolID": symbol_id,
    })
```

---

## 6. CODE ISSUES FOUND

### Hardcoded Paths (Non-portable)

**File**: `config/settings.py`

```python
CSV_FEED_PATH = r"C:\Users\cgrah\Desktop\APPSIERRA\data\snapshot.csv"
STATE_PATH = r"C:\Users\cgrah\Desktop\APPSIERRA\data\runtime_state_panel2.json"
```

**Issue**: Won't work on other machines or operating systems

**Fix**: Use `Path.home()` or environment variables

---

### Unused Callbacks

- `on_md_trade` - defined but never used
- `on_md_bidask` - defined but never used
- `on_security_definition` - defined but never used
- `on_positions_seed_done` - defined but never used
- `on_orders_seed_done` - defined but never used

---

### Missing Error Handling

- OrderReject messages cause silent failures
- OrderCancelReject messages cause silent failures
- MarketDataReject causes silent failures
- No dialog notifications for user awareness

---

## 7. IMPLEMENTATION SUMMARY TABLE

| Feature                   | Status    | Location           | Impact       |
| ------------------------- | --------- | ------------------ | ------------ |
| **Connection Mgmt**       | ✓ DONE    | data_bridge.py     | Working      |
| **Heartbeat/Keepalive**   | ✓ DONE    | data_bridge.py     | Working      |
| **Account Info**          | ✓ DONE    | dtc_json_client.py | Working      |
| **Position Updates**      | ✓ DONE    | dtc_json_client.py | Working      |
| **Order Status**          | ✓ DONE    | dtc_json_client.py | Working      |
| **Historical Fills**      | ✓ DONE    | dtc_json_client.py | Working      |
| **Balance Updates**       | ✓ DONE    | dtc_json_client.py | Working      |
| **Market Data (Bid/Ask)** | ◐ PARTIAL | dtc_json_client.py | Working      |
| **Market Data (Session)** | ✗ MISSING | -                  | Critical     |
| **ORDER SUBMISSION**      | ✗ MISSING | -                  | **CRITICAL** |
| **ORDER CANCELLATION**    | ✗ MISSING | -                  | **CRITICAL** |
| **ORDER MODIFICATION**    | ✗ MISSING | -                  | **CRITICAL** |
| **Security Definitions**  | ◐ PARTIAL | dtc_json_client.py | Partial      |
| **Symbol Lookup**         | ✗ MISSING | -                  | Missing      |
| **State Persistence**     | ✗ BROKEN  | state_manager.py   | Broken       |
| **Dynamic MD Subscribe**  | ✗ MISSING | -                  | Missing      |
| **Historical Price Data** | ✗ MISSING | -                  | Missing      |
| **Order Reject Handling** | ✗ MISSING | -                  | Missing      |

---

## 8. IMPLEMENTATION ROADMAP

### Phase 1: CRITICAL (Required for Trading)

- [ ] Implement `submit_order()` in DTCClientJSON
- [ ] Implement `cancel_order()` in DTCClientJSON
- [ ] Complete StateManager methods (update_balance, update_position, record_order)
- [ ] Add order submission UI (button/dialog in Panel2)
- [ ] Add order cancellation UI (context menu in Panel2)

### Phase 2: HIGH PRIORITY

- [ ] Implement `modify_order()` in DTCClientJSON
- [ ] Add symbol search/lookup interface
- [ ] Dispatch session market data updates (120-124)
- [ ] Add order rejection/cancel rejection handling with notifications
- [ ] Fix hardcoded paths in settings.py (use Path.home())

### Phase 3: MEDIUM PRIORITY

- [ ] Wire security definition responses to display contract specs
- [ ] Implement dynamic market data subscribe/unsubscribe
- [ ] Add historical price data handlers
- [ ] Add symbol validation before order submission
- [ ] Implement order confirmation workflow

### Phase 4: POLISH

- [ ] Add error dialogs for trading failures
- [ ] Add TODO/FIXME comments for tracking
- [ ] Add detailed logging for all DTC operations
- [ ] Create unit tests for order submit/cancel
- [ ] Document DTC message schemas

---

## Files Involved in DTC Integration

### Core DTC Implementation

- `/services/dtc_json_client.py` - Main DTC client (667 lines)
- `/core/data_bridge.py` - Qt-based DTC wrapper (370 lines)
- `/core/app_manager.py` - DTC initialization and wiring

### UI Panels (Data Consumers)

- `/panels/panel1.py` - Balance & investing
- `/panels/panel2.py` - Live trading (3800+ lines)
- `/panels/panel3.py` - Trading statistics

### Supporting Infrastructure

- `/core/message_router.py` - Dispatch DTC events to panels
- `/core/state_manager.py` - App state (incomplete)
- `/services/trade_store.py` - Persist trades to database
- `/services/stats_service.py` - Compute trading statistics
- `/services/market_joiner.py` - CSV market data bridge
- `/data/schema.py` - Database schema (TradeRecord, etc.)

### Configuration

- `/config/settings.py` - DTC host/port, account settings (HARDCODED PATHS!)

---

## Conclusion

APPSIERRA has a **solid foundation for a trading application** with working:

- Connection management
- Data reception and persistence
- Statistics calculation
- Multi-timeframe analysis

However, it is **incomplete for actual trading** due to missing:

- Order submission capability
- Order cancellation capability
- Order modification capability
- Complete state management
- Symbol lookup functionality
- Proper error handling and notifications

**Estimated Effort to Complete**:

- Phase 1 (Critical): 16-20 hours
- Phase 2 (High Priority): 12-16 hours
- Phase 3 (Medium Priority): 8-12 hours
- Phase 4 (Polish): 8-12 hours
- **Total**: 44-60 hours to full trading capability

**Minimum for Basic Trading**: 20-24 hours (Phase 1 complete)
