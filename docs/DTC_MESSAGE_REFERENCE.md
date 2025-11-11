# DTC Protocol Message Reference

**Complete mapping of all message types Sierra Chart sends**

Discovered via comprehensive DTC discovery tool on 2025-11-08.

---

## Message Type Overview

Sierra Chart sends **7 distinct message types** in response to various requests:

| Type | Name                 | Frequency        | Source                                    |
| ---- | -------------------- | ---------------- | ----------------------------------------- |
| 2    | LogonResponse        | Once             | Server response to Logon                  |
| 3    | Heartbeat            | Periodic         | Unsolicited (keep-alive)                  |
| 306  | PositionUpdate       | Multiple         | Response to Type 305 (OpenOrders) **BUG** |
| 308  | TradeAccountResponse | Once per request | Response to Type 303 (Fill requests)      |
| 401  | TradeAccountResponse | Multiple         | Response to Type 400 (TradeAccounts)      |
| 501  | MarketDataSnapshot   | Continuous       | Response to Type 500 (Positions) stream   |
| 600  | AccountBalanceUpdate | Once per request | Response to Type 601 (Balance)            |

---

## Detailed Message Specifications

### Type 2: LogonResponse

**Purpose:** Confirms successful connection and authentication
**Request:** Type 1 (LogonRequest)
**Count:** 1 per session
**Sample Fields:** 20 total

- ProtocolVersion
- Result (1 = success)
- ServerName
- TradingIsSupported (0 in SIM mode)
- MarketDataSupported

**Key Finding:** `TradingIsSupported: 0` indicates SIM mode (read-only)

---

### Type 3: Heartbeat

**Purpose:** Keep-alive signal, no action needed
**Frequency:** Every 5 seconds (configurable)
**Fields:** Minimal (2 fields)

- Type: 3
- F: [timing/status array]

**Key Finding:** Safe to ignore; used for connection keep-alive only

---

### Type 306: PositionUpdate

**Purpose:** Position information
**REQUEST SOURCE:** Type 305 (OpenOrdersRequest) ⚠️ **PROTOCOL VIOLATION**
**Count:** 5 messages (one per previously traded symbol)
**Fields:** 19 total

**Critical Issue:** Sierra returns Type 306 in response to Type 305 (OpenOrders), mixing position data with order responses. This is incorrect per DTC protocol.

**Sample Structure:**

```json
{
  "Type": 306,
  "RequestID": 102,
  "TotalNumberMessages": 5,
  "MessageNumber": 1-5,
  "Symbol": "F.US.MESM25",
  "Quantity": 0 or 1,
  "AveragePrice": 5996.5,
  "TradeAccount": "Sim1",
  "MarginRequirement": 0,
  "OpenProfitLoss": 0
}
```

**Fields:**

- Symbol
- Quantity (0 = closed position)
- AveragePrice (entry price)
- TradeAccount
- MessageNumber (part of sequence)
- TotalNumberMessages (total in sequence)
- OpenProfitLoss
- HighPriceDuringPosition
- LowPriceDuringPosition
- PositionIdentifier
- EntryDateTime
- QuantityLimit
- MaxPotentialPostionQuantity
- MarginRequirement
- NoPositions (0 = has positions)

**FIX IN APP:** Reject Type 306 messages with RequestID=3 (these are incorrect responses to OpenOrdersRequest)

---

### Type 308: TradeAccountResponse

**Purpose:** Response to Type 303 (HistoricalOrderFillRequest)
**Count:** 1 per request
**Fields:** 3 minimal

- Type: 308
- RequestID: (echoed from request)
- RejectText: "TradeAccount is not set" (error message)

**Key Finding:** If TradeAccount not specified in Type 303 request, returns rejection

---

### Type 401: TradeAccountResponse

**Purpose:** List available trading accounts
**Request:** Type 400 (TradeAccountsRequest)
**Count:** Multiple (one per account)
**Fields:** 6 total

**Sample Structure:**

```json
{
  "Type": 401,
  "TotalNumberMessages": 2,
  "MessageNumber": 1-2,
  "TradeAccount": "120005" or "Sim1",
  "RequestID": 100,
  "TradingIsDisabled": 0
}
```

**Fields:**

- TradeAccount (account identifier)
- TradingIsDisabled (0 = enabled)
- MessageNumber (sequence number)
- TotalNumberMessages (total in sequence)

**Key Finding:** Returns multiple responses - one per account available

---

### Type 501: MarketDataSnapshot

**Purpose:** Live market data stream (bid/ask/trade updates)
**Request:** Type 500 (PositionsRequest) or continuous subscription
**Count:** 34+ messages (continuous stream)
**Fields:** 5 total (minimal)

**Sample Structure:**

```json
{
  "Type": 501,
  "RequestID": 101,
  "Exchange": "BMDX",
  "Description": "",
  "IsFinalMessage": 0
}
```

**Fields:**

- Type: 501
- RequestID: (echoed from request)
- Exchange: (symbol exchange)
- Description: (symbol description)
- IsFinalMessage: (0 = more coming, 1 = end of stream)

**Key Finding:** This is the ONLY response to Type 500 PositionsRequest - NO Type 306 position data returns here. Sierra sends market data, not position data.

---

### Type 600: AccountBalanceUpdate

**Purpose:** Account balance and margin information
**Request:** Type 601 (AccountBalanceRequest)
**Count:** 1 per request
**Fields:** 31 total (comprehensive)

**Sample Structure:**

```json
{
  "Type": 600,
  "RequestID": 104,
  "TradeAccount": "120005",
  "CashBalance": 21.66,
  "BalanceAvailableForNewPositions": 21.66,
  "SecuritiesValue": 21.66,
  "MarginRequirement": 0,
  "OpenPositionsProfitLoss": 0,
  "DailyProfitLoss": 0,
  "TradingIsDisabled": 0
}
```

**Key Balance Fields:**

- CashBalance (available cash)
- BalanceAvailableForNewPositions (buying power)
- SecuritiesValue (value of open positions)
- MarginRequirement (total margin required)
- OpenPositionsProfitLoss (unrealized P&L)
- DailyProfitLoss (day's P&L)
- IsUnderRequiredMargin (1 = danger)
- IsUnderRequiredAccountValue (1 = danger)

**Key Finding:** Comprehensive balance info in single response

---

## Request/Response Mapping

### What Each Request Returns

| Request Type | Request Name          | Expected Response       | Actually Receives               |
| ------------ | --------------------- | ----------------------- | ------------------------------- |
| Type 1       | LogonRequest          | Type 2 (LogonResponse)  | Type 2 ✓                        |
| Type 400     | TradeAccountsRequest  | Type 401 (TradeAccount) | Type 401 ✓                      |
| Type 500     | PositionsRequest      | Type 306 (Positions)    | Type 501 (MarketData) ⚠️        |
| Type 305     | OpenOrdersRequest     | Type 301 (Orders)       | Type 306 (Positions) ❌ **BUG** |
| Type 303     | HistoricalFillRequest | Type 304 (Fills)        | Type 308 (Reject) ❌            |
| Type 601     | AccountBalanceRequest | Type 602 (Balance)      | Type 600 (Balance) ✓            |

---

## Key Findings & Protocol Violations

### 1. No Type 306 in Position Request Response

- Request: Type 500 (PositionsRequest)
- Expected: Type 306 (PositionUpdate) messages
- Actual: Type 501 (MarketDataSnapshot) messages
- **Impact:** Position data not sent in response to position requests

### 2. Type 306 Returned from Wrong Request

- Request: Type 305 (OpenOrdersRequest)
- Expected: Type 301 (OrderUpdate) messages
- Actual: Type 306 (PositionUpdate) messages
- **Impact:** Position data mixed with order responses (CAUSES PHANTOM POSITIONS)

### 3. Historical Fills Request Fails

- Request: Type 303 (HistoricalOrderFillRequest) without TradeAccount
- Expected: Type 304 (HistoricalOrderFillResponse)
- Actual: Type 308 RejectText "TradeAccount is not set"
- **Impact:** Cannot query fills without specifying account

### 4. MarketData is the Position Response

- Type 501 is returned instead of Type 306 for position queries
- This contains bid/ask/trade info, not position data
- **Impact:** Positions must be reconstructed from order fills, not queried directly

---

## Recommended Handling

### In Application Code

1. **Reject Type 306 from RequestID 3 (OpenOrders)**

   ```python
   if msg_type == 306 and request_id == 3:
       log.warning("Reject spurious Type 306 from OpenOrders request")
       return  # Skip processing
   ```

2. **Reconstruct Positions from Order Fills**
   - Use Type 301 (OrderUpdate) and Type 304 (Fill responses)
   - Build position table from order execution history
   - Don't rely on Type 306 position messages

3. **Use Type 501 for Market Data Only**
   - MarketDataSnapshot provides real-time bid/ask/trade updates
   - Not position position data

4. **Always Specify TradeAccount for Fills**
   - Type 303 requests need TradeAccount parameter
   - Otherwise returns Type 308 rejection

---

## Complete Field List by Message Type

See discovery tool output for exhaustive field listing.

Most important fields extracted above for each type.

---

**Discovery Date:** 2025-11-08
**Sierra Chart Version:** [From connected instance]
**Protocol Version:** 8
**Tool:** discover_all_dtc_messages.py
