# APPSIERRA DTC SCHEMA - RECOMMENDED FIXES

This document provides step-by-step instructions for applying the recommended fixes identified in the schema audit.

---

## FIX #1: PositionUpdate.UpdateReason Type Mismatch ⚠️ CRITICAL

**Severity:** MEDIUM
**File:** `services/dtc_schemas.py`
**Lines:** 263
**Time to Fix:** 5 minutes

### Problem

The `UpdateReason` field is defined as `Optional[str]` but should be `Optional[int]` to match the `PositionUpdateReasonEnum` enum defined at lines 62-66.

### Current Code

```python
# Line 263
UpdateReason: Optional[str] = None  # String in DTC (not enum)
```

### Recommended Fix

```python
# Line 263
UpdateReason: Optional[int] = None  # Maps to PositionUpdateReasonEnum (0, 1, 2)
```

### Why This Matters

- **Type Consistency:** The field should match the enum type
- **Validation:** Enables proper type checking and IDE code completion
- **Documentation:** Makes the intent clear to developers

### How to Apply

1. Open `services/dtc_schemas.py`
2. Go to line 263
3. Change `UpdateReason: Optional[str]` to `UpdateReason: Optional[int]`
4. Save the file
5. Run tests: `python -m unittest tests.test_schema_integrity_standalone -v`

### Test Validation

Add this test to verify the fix:

```python
def test_position_update_reason_type(self):
    """Verify UpdateReason is int type"""
    payload = {
        "Type": 306,
        "Symbol": "MESZ24",
        "UpdateReason": 0,  # UNSOLICITED
    }
    pos = PositionUpdate.model_validate(payload)
    self.assertEqual(pos.UpdateReason, 0)
    self.assertIsInstance(pos.UpdateReason, int)
```

---

## FIX #2: Add Validators for OrderType and OrderStatus 🟡 HIGH PRIORITY

**Severity:** LOW-MEDIUM
**File:** `services/dtc_schemas.py`
**Location:** Within OrderUpdate class (after line 155)
**Time to Fix:** 20 minutes

### Problem

Only `BuySell` field has validation. `OrderType` and `OrderStatus` should also validate against enum ranges.

### Current Code (Lines 150-155)

```python
@field_validator("BuySell", mode="before")
@classmethod
def validate_buy_sell(cls, v):
    if v is not None and v not in [1, 2]:
        return None
    return v
```

### Recommended Addition

Add these validators right after the BuySell validator:

```python
@field_validator("OrderType", mode="before")
@classmethod
def validate_order_type(cls, v):
    """Validate OrderType is 1-5 (Market, Limit, Stop, StopLimit, MIT)"""
    if v is not None and v not in [1, 2, 3, 4, 5]:
        return None
    return v

@field_validator("OrderStatus", mode="before")
@classmethod
def validate_order_status(cls, v):
    """Validate OrderStatus is 0-9 (valid DTC order statuses)"""
    if v is not None and v not in range(0, 10):
        return None
    return v

@field_validator("OrderUpdateReason", mode="before")
@classmethod
def validate_order_update_reason(cls, v):
    """Validate OrderUpdateReason is 0-9 (valid DTC update reasons)"""
    if v is not None and v not in range(0, 10):
        return None
    return v
```

### How to Apply

1. Open `services/dtc_schemas.py`
2. Go to line 155 (after `validate_buy_sell` method)
3. Add the three new validator methods above
4. Save the file
5. Run tests to verify: `python -m unittest tests.test_schema_integrity_standalone TestOrderUpdateSchema -v`

### Test Validation

```python
def test_invalid_order_type_validation(self):
    """Invalid OrderType value should be set to None"""
    payload = {"Type": 301, "ServerOrderID": "TEST", "OrderType": 999}
    order = OrderUpdate.model_validate(payload)
    self.assertIsNone(order.OrderType)

def test_invalid_order_status_validation(self):
    """Invalid OrderStatus value should be set to None"""
    payload = {"Type": 301, "ServerOrderID": "TEST", "OrderStatus": 999}
    order = OrderUpdate.model_validate(payload)
    self.assertIsNone(order.OrderStatus)
```

---

## FIX #3: Document Field Name Variants in Comments 🟡 HIGH PRIORITY

**Severity:** LOW
**File:** `services/dtc_schemas.py`
**Location:** OrderUpdate class (around lines 104-138)
**Time to Fix:** 30 minutes

### Problem

The schema has multiple aliases for the same logical field (e.g., 5 price variants, 3 quantity variants) but this is not documented. New developers may be confused about which field name to use.

### Current Code Example (Lines 104-116)

```python
# Quantities
OrderQuantity: Optional[float] = None
Quantity: Optional[float] = None  # Alias
TotalQuantity: Optional[float] = None  # Alias
FilledQuantity: Optional[float] = None
RemainingQuantity: Optional[float] = None

# Prices
Price1: Optional[float] = None  # Primary price (limit/stop)
Price2: Optional[float] = None  # Secondary price (stop-limit)
Price: Optional[float] = None  # Alias
LimitPrice: Optional[float] = None  # Alias
StopPrice: Optional[float] = None  # Alias
```

### Recommended Enhancement

Add detailed comments explaining the alias hierarchy:

```python
# Quantities (use get_quantity() helper to coalesce)
# Priority: OrderQuantity > Quantity > TotalQuantity
OrderQuantity: Optional[float] = None  # Primary field (use this for new orders)
Quantity: Optional[float] = None  # Alias for OrderQuantity (may appear from older Sierra versions)
TotalQuantity: Optional[float] = None  # Alias for OrderQuantity (may appear from some DTC servers)
FilledQuantity: Optional[float] = None  # Amount actually filled
RemainingQuantity: Optional[float] = None  # Amount still open

# Prices (use get_price() helper to coalesce)
# Priority: Price1 > Price > LimitPrice > StopPrice
# Note: Price2 is different (secondary/limit price for stop-limit orders)
Price1: Optional[float] = None  # Primary price field (limit/stop/trigger price)
Price2: Optional[float] = None  # Secondary price (limit price for stop-limit orders only)
Price: Optional[float] = None  # Alias for Price1 (may appear from older Sierra versions)
LimitPrice: Optional[float] = None  # Alias for Price1 (semantic when order is limit type)
StopPrice: Optional[float] = None  # Alias for Price1 (semantic when order is stop type)
```

Add a module-level comment at the top:

```python
"""
Field Alias Information
======================

The DTC protocol messages from Sierra Chart may use different field names
for the same logical data, depending on the Sierra Chart version. This schema
handles all known variants using field aliases.

Common Alias Groups:
- Quantity: OrderQuantity, Quantity, TotalQuantity (use get_quantity())
- Price: Price1, Price, LimitPrice, StopPrice (use get_price())
- Average Fill Price: AverageFillPrice, AvgFillPrice (use get_avg_fill_price())
- High/Low During Position: HighDuringPosition, HighPriceDuringPosition (use get_high/low_during_position())
- Text: InfoText, TextMessage, FreeFormText, RejectText (use get_text())

The helper methods at the end of the OrderUpdate class automatically coalesce
these aliases with priority ordering to simplify data extraction.
"""
```

### How to Apply

1. Open `services/dtc_schemas.py`
2. Add the module-level comment after line 5 (after existing docstring)
3. Update field comments in OrderUpdate class (lines 104-138)
4. Save the file
5. No functional changes needed - this is documentation only

---

## FIX #4: Change Config.extra from "allow" to "warn" 🟡 MEDIUM PRIORITY

**Severity:** LOW
**File:** `services/dtc_schemas.py`
**Lines:** 75-77
**Time to Fix:** 10 minutes

### Problem

Current configuration silently accepts unknown fields with `extra = "allow"`. This may mask changes in the DTC protocol or surprises from Sierra Chart.

### Current Code

```python
class Config:
    extra = "allow"  # Allow additional fields not in schema
    use_enum_values = True
```

### Recommended Option A: Use "warn" (Pydantic v2)

```python
class Config:
    extra = "warn"  # Warn on unknown fields
    use_enum_values = True
```

**Note:** Pydantic v2 uses `ConfigDict` instead of `Config` class. If using v2, use:

```python
model_config = ConfigDict(
    extra="forbid",  # Or "warn" - reject unknown fields
    use_enum_values=True,
    validate_assignment=True,
)
```

### Recommended Option B: Custom Logging (Production-Safe)

Keep `extra = "allow"` but add logging for unknown fields:

```python
@model_validator(mode="after")
def log_unknown_fields(self):
    """Log any fields not in the schema"""
    known_fields = set(self.model_fields.keys())
    actual_fields = set(self.__dict__.keys())
    unknown = actual_fields - known_fields
    if unknown:
        import logging
        logger = logging.getLogger(__name__)
        logger.debug(f"Unknown fields in {self.__class__.__name__}: {unknown}")
    return self
```

### How to Apply

**Option A (Change Config):**

1. Open `services/dtc_schemas.py`
2. Line 76: Change `extra = "allow"` to `extra = "warn"`
3. Save and test

**Option B (Add Logging):**

1. Add logging import at top of file (if not present)
2. Add the `log_unknown_fields` method to DTCMessage class
3. Unknown fields will be logged at DEBUG level

### Why This Matters

- **Protocol Monitoring:** Catches unexpected field changes from Sierra Chart
- **Debugging:** Easier to identify mismatch between schema and reality
- **Safety:** Warns if DTC protocol changes

---

## FIX #5: Document Timestamp Format 🟡 MEDIUM PRIORITY

**Severity:** LOW
**File:** `services/dtc_schemas.py`
**Location:** Lines 132-133 (and other timestamp fields)
**Time to Fix:** 15 minutes

### Problem

Timestamp fields are `Optional[float]` but the format (Unix seconds? microseconds?) is not documented.

### Current Code

```python
# Timestamps
OrderReceivedDateTime: Optional[float] = None  # Unix timestamp
LatestTransactionDateTime: Optional[float] = None  # Unix timestamp
```

### Recommended Enhancement

Add clarity about the exact format:

```python
# Timestamps (Unix epoch time)
# Note: Sierra Chart uses seconds since epoch (not milliseconds or microseconds)
# Example: 1730822500.0 = Nov 5, 2024 at 5:01:40 PM UTC
OrderReceivedDateTime: Optional[float] = None  # Unix timestamp (seconds), order received time
LatestTransactionDateTime: Optional[float] = None  # Unix timestamp (seconds), most recent update time
```

For the `get_timestamp()` helper, add a comment:

```python
def get_timestamp(self) -> Optional[float]:
    """
    Returns best available timestamp (Unix seconds since epoch).

    Priority: LatestTransactionDateTime > OrderReceivedDateTime

    To convert to datetime: datetime.fromtimestamp(timestamp, tz=timezone.utc)
    """
    return self.LatestTransactionDateTime or self.OrderReceivedDateTime
```

### How to Apply

1. Open `services/dtc_schemas.py`
2. Update comments on timestamp fields (lines 132-133, 123)
3. Add docstring to `get_timestamp()` method (around line 214)
4. Add example conversion comment
5. Save the file

---

## VERIFICATION CHECKLIST

After applying fixes, verify with this checklist:

- [ ] **Fix #1 Applied:** PositionUpdate.UpdateReason is `Optional[int]`

  ```bash
  grep "UpdateReason: Optional\[int\]" services/dtc_schemas.py
  ```

- [ ] **Fix #2 Applied:** Validators added for OrderType, OrderStatus, OrderUpdateReason

  ```bash
  grep "@field_validator" services/dtc_schemas.py | wc -l
  # Should show 4 validators (BuySell, OrderType, OrderStatus, OrderUpdateReason)
  ```

- [ ] **Fix #3 Applied:** Comments updated with alias documentation

  ```bash
  grep -A2 "Priority:" services/dtc_schemas.py
  ```

- [ ] **Fix #4 Applied (if chosen):** Config.extra updated

  ```bash
  grep "extra = " services/dtc_schemas.py
  ```

- [ ] **Fix #5 Applied:** Timestamp documentation added

  ```bash
  grep "seconds since epoch" services/dtc_schemas.py
  ```

- [ ] **Tests Pass:** Run the test suite

  ```bash
  python -m unittest tests.test_schema_integrity_standalone -v
  ```

---

## APPLYING FIXES IN ORDER

**Recommended order of application:**

1. **FIX #1 (5 min)** - Critical type fix
2. **FIX #2 (20 min)** - Add validators
3. **FIX #5 (15 min)** - Document timestamps
4. **FIX #3 (30 min)** - Document aliases
5. **FIX #4 (10 min)** - Update Config (optional)

**Total Time:** ~60 minutes

---

## ROLLBACK PLAN

If any fix causes issues:

1. **Git:** Revert to previous commit

   ```bash
   git revert <commit-hash>
   ```

2. **Manual:** Undo the specific change
   - Fix #1: Change `Optional[int]` back to `Optional[str]`
   - Fix #2: Remove the new validator methods
   - Fix #3: Remove the added comments
   - Fix #4: Change `extra = "warn"` back to `extra = "allow"`
   - Fix #5: Remove timestamp documentation

3. **Test:** Re-run tests to confirm

   ```bash
   python -m unittest tests.test_schema_integrity_standalone -v
   ```

---

## QUESTIONS?

Refer back to:

- **SCHEMA_AUDIT_REPORT.md** - Full audit details
- **AUDIT_SUMMARY.md** - Quick reference
- **test_schema_integrity_standalone.py** - Test examples

---

**End of Recommended Fixes**
