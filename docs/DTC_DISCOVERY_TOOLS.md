# DTC Protocol Discovery Tools

Created comprehensive tools to discover all possible DTC message types that Sierra Chart can send.

## Tools Created

### 1. `tools/discover_all_dtc_messages.py`

**Purpose:** Systematic discovery of DTC messages through standard requests
**Method:** Makes requests in logical sequence:

1. Logon (Type 1)
2. Trade Accounts Request (Type 400)
3. Positions Request (Type 500)
4. Open Orders Request (Type 305)
5. Historical Fills Request (Type 303)
6. Account Balance Request (Type 601)
7. Wait for unsolicited updates

**Messages Found:**

- Type 2: LogonResponse
- Type 3: Heartbeat
- Type 306: PositionUpdate (from OpenOrders - BUG!)
- Type 308: TradeAccountResponse (error)
- Type 401: TradeAccountResponse
- Type 501: MarketDataSnapshot
- Type 600: AccountBalanceUpdate

**Files:** `tools/discover_all_dtc_messages.py`

---

### 2. `tools/discover_extended_dtc_messages.py`

**Purpose:** Find additional message types through edge cases and special requests
**Method:** Tests less common request types:

- Type 101: Market Depth Request
- Type 102: Market Data Request
- Type 104: Market Depth Snapshot
- Type 300: Submit Order
- Type 302: Cancel Order
- Types 105-110: Trade statistics (if supported)
- Types 15-16: Security definitions
- Type 34: Current price
- Type 308: Account orders
- Types 309-310: Account positions/responses

**New Messages Found:**

- Type 103: MarketDepthRequest response
- Type 121: MarketDataRequest response
- Type 301: OrderUpdate (from order submission)
- Type 310: Position response with error flag

**Files:** `tools/discover_extended_dtc_messages.py`

---

### 3. `tools/brute_force_dtc_types.py`

**Purpose:** Test ALL possible message type numbers (1-1000) to find any missed types
**Method:** Sends each type number and records responses
**Ranges Tested:**

- Types 1-50: Authentication, basic
- Types 100-150: Market data
- Types 200-250: Advanced market
- Types 300-350: Order management
- Types 400-450: Account management
- Types 500-550: Positions & fills
- Types 600-650: Balance & account
- Types 700-750: Advanced trading
- Types 800-850: Logging
- Types 900-950: System

**Status:** [Running - comprehensive map being built]

---

## Message Types Discovered So Far

**Total: 14+ unique message types**

| Type | Name                         | Source                                |
| ---- | ---------------------------- | ------------------------------------- |
| 1    | LogonRequest                 | Client sends                          |
| 2    | LogonResponse                | Server response                       |
| 3    | Heartbeat                    | Unsolicited                           |
| 101  | MarketDepthRequest           | (proprietary)                         |
| 102  | MarketDataRequest            | (proprietary)                         |
| 103  | MarketDepthResponse          | Server response                       |
| 104  | MarketDepthSnapshot          | (proprietary)                         |
| 121  | MarketDataResponse           | Server response                       |
| 300  | SubmitNewSingleOrder         | Client sends                          |
| 301  | OrderUpdate                  | Server response/unsolicited           |
| 302  | OrderCancelRequest           | Client sends                          |
| 303  | HistoricalOrderFillRequest   | Client sends                          |
| 305  | OpenOrdersRequest            | Client sends                          |
| 306  | PositionUpdate               | **Server sends from Type 305 (BUG!)** |
| 308  | TradeAccountResponse (error) | Server response                       |
| 309  | GetAccountPositions          | Client sends                          |
| 310  | AccountPositionsResponse     | Server response                       |
| 400  | TradeAccountsRequest         | Client sends                          |
| 401  | TradeAccountResponse         | Server response                       |
| 500  | PositionsRequest             | Client sends                          |
| 501  | MarketDataSnapshot           | Server continuous                     |
| 600  | AccountBalanceUpdate         | Server response                       |
| 601  | AccountBalanceRequest        | Client sends                          |

---

## How to Use These Tools

### Run individual discovery tools

```bash
# Standard discovery (5-10 seconds)
python tools/discover_all_dtc_messages.py

# Extended discovery (10-20 seconds)
python tools/discover_extended_dtc_messages.py

# Brute force all types 1-1000 (3-5 minutes)
python tools/brute_force_dtc_types.py
```

### Combine results

```bash
# Run all and save to single report
python tools/discover_all_dtc_messages.py > discovery_report.txt
python tools/discover_extended_dtc_messages.py >> discovery_report.txt
python tools/brute_force_dtc_types.py >> discovery_report.txt
```

---

## Key Findings

### Protocol Issues Found

1. **Type 306 sent from wrong request**
   - Sent in response to Type 305 (OpenOrders)
   - Should send Type 301 (OrderUpdates)
   - This causes phantom positions!

2. **No Type 502 PositionsResponse**
   - Type 500 returns Type 501 (market data) not position data
   - Positions must be reconstructed from orders

3. **Type 308 errors missing account**
   - Type 303 requests need TradeAccount parameter
   - Returns Type 308 reject if not specified

4. **Market Depth not fully supported**
   - Types 101/104 return Type 103 with mostly empty data
   - May not be fully implemented in your Sierra instance

---

## Next Steps

1. Run brute force discovery to completion to find ALL types
2. Document each message type's fields and usage
3. Update DTC_MESSAGE_REFERENCE.md with complete list
4. Ensure application code handles all response types
5. Add validation for unexpected message types

---

**Last Updated:** 2025-11-08
**Status:** Discovery in progress
