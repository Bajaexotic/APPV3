# DTC Pydantic Ledger System

Python replacement for PowerShell `dtc_build_ledgers.ps1` with type-safe Pydantic models.

## Files

- **`dtc_schemas.py`** - Pydantic models for DTC message types (301, 306, 600, etc.)
- **`dtc_ledger.py`** - Order state tracking and ledger builder
- **`dtc_report_cli.py`** - CLI tool for generating reports

## Features

✅ **Type Safety** - Pydantic validation catches malformed DTC messages
✅ **Order Tracking** - Groups Type 301 messages by ServerOrderID
✅ **Terminal Status** - Finds most final state (Filled/Canceled/Rejected priority)
✅ **Fill Stream** - Chronological fill events
✅ **Exit Detection** - Automatically detects Stop/Limit/Market exits
✅ **CSV/JSON Export** - Multiple output formats

## Usage

### CLI Tool

```bash
# Generate all 3 CSV reports
python -m services.dtc_report_cli --input logs/dtc_live_orders.jsonl

# Generate JSON output
python -m services.dtc_report_cli --input logs/dtc.jsonl --format json

# Custom output directory
python -m services.dtc_report_cli --input logs/dtc.jsonl --output-dir ~/reports/

# Ledger only (skip snapshot and fills)
python -m services.dtc_report_cli --input logs/dtc.jsonl --ledger-only
```

### Python API

```python
from services.dtc_ledger import OrderLedgerBuilder, read_dtc_jsonl

# Read Type 301 messages from JSONL
updates = read_dtc_jsonl("logs/dtc_live_orders.jsonl")

# Build ledger
builder = OrderLedgerBuilder(updates)

# Get reports
ledger = builder.build_ledger()      # Terminal state for each order
snapshot = builder.build_snapshot()  # Latest update for each order
fills = builder.build_fill_stream()  # Chronological fill events

# Export to CSV
from services.dtc_ledger import export_to_csv
export_to_csv(ledger, "reports/order_ledger.csv")
export_to_csv(fills, "reports/fills.csv")
```

### Pydantic Schemas

```python
from services.dtc_schemas import OrderUpdate, parse_dtc_message

# Parse a raw DTC message
raw = {"Type": 301, "ServerOrderID": "12345", "Symbol": "MESZ24", "BuySell": 1}
order = parse_dtc_message(raw)

# Type-safe access
print(order.Symbol)           # "MESZ24"
print(order.get_side())       # "Buy"
print(order.get_status())     # "Filled"
print(order.is_terminal())    # True if Filled/Canceled/Rejected

# Validation
try:
    order = OrderUpdate.model_validate(raw)
except ValidationError as e:
    print(f"Invalid message: {e}")
```

## Report Types

### 1. Order Ledger Summary (`dtc_order_ledger_summary.csv`)

Terminal state for each unique order (grouped by ServerOrderID):

| Field           | Description                                     |
| --------------- | ----------------------------------------------- |
| server_order_id | Unique order identifier                         |
| symbol          | Trading symbol (e.g., MESZ24)                   |
| trade_account   | Account name (e.g., 120005, Sim1)               |
| side            | "Buy" or "Sell"                                 |
| order_type      | "Market", "Limit", "Stop", "StopLimit"          |
| qty             | Order quantity                                  |
| price           | Order price                                     |
| filled_qty      | Total filled quantity                           |
| avg_fill_price  | Average fill price                              |
| status          | Final status (Filled, Canceled, Rejected, etc.) |
| reason          | Update reason (NewAccepted, Filled, etc.)       |
| exit_kind       | "Stop", "Limit", or "Market" (only on fills)    |
| high_during_pos | Highest price during position                   |
| low_during_pos  | Lowest price during position                    |
| first_time      | First update timestamp (Unix epoch)             |
| last_time       | Last update timestamp (Unix epoch)              |
| duration_sec    | Order lifetime in seconds                       |
| text            | InfoText/RejectText if present                  |

### 2. Latest Snapshot (`dtc_order_snapshot_latest.csv`)

Most recent update for each order:

| Field           | Description    |
| --------------- | -------------- |
| server_order_id | Order ID       |
| symbol          | Symbol         |
| trade_account   | Account        |
| side            | Buy/Sell       |
| order_type      | Order type     |
| qty             | Quantity       |
| price           | Price          |
| status          | Current status |
| reason          | Update reason  |
| text            | Text/Info      |

### 3. Fill Stream (`dtc_fills.csv`)

Chronological fill events (sorted by time):

| Field           | Description                   |
| --------------- | ----------------------------- |
| time            | Fill timestamp (Unix epoch)   |
| server_order_id | Order ID                      |
| symbol          | Symbol                        |
| trade_account   | Account                       |
| side            | Buy/Sell                      |
| order_type      | Order type                    |
| last_fill_qty   | Quantity filled in this event |
| last_fill_price | Fill price                    |
| status          | Order status after fill       |
| reason          | Update reason                 |
| text            | Text/Info                     |

## Terminal Status Priority

Orders are ranked by "finality" - more terminal statuses override less final ones:

**Rank 5 (Most Final)**:

- Filled (7)
- Rejected (8)
- Canceled (6)

**Rank 4**:

- PartiallyFilled (9)

**Rank 3**:

- Open (4)

**Rank 2**:

- Submitted (2)

**Rank 1 (Least Final)**:

- New (1)
- PendingCancel (3)
- PendingReplace (5)

When multiple updates exist for the same order, the system chooses the update with:

1. Highest terminal rank
2. Latest timestamp (tie-breaker)

## Migration from PowerShell

The Python system provides identical functionality to `dtc_build_ledgers.ps1`:

| PowerShell Function    | Python Equivalent                        |
| ---------------------- | ---------------------------------------- |
| `Read-DtcJsonl`        | `read_dtc_jsonl()`                       |
| `Build-OrderLedger`    | `OrderLedgerBuilder.build_ledger()`      |
| `Build-LatestSnapshot` | `OrderLedgerBuilder.build_snapshot()`    |
| `Build-FillStream`     | `OrderLedgerBuilder.build_fill_stream()` |
| `Export-Csv`           | `export_to_csv()`                        |

### Benefits over PowerShell

- ✅ Type safety with Pydantic validation
- ✅ Better error messages
- ✅ IDE autocomplete for DTC fields
- ✅ Cross-platform (Linux/Mac/Windows)
- ✅ Integrated with Python app
- ✅ JSON export in addition to CSV
- ✅ Can be imported as Python module

## Testing

Sample test data is provided in `test_data/sample_dtc_orders.jsonl`.

```bash
# Run test
python -m services.dtc_report_cli --input test_data/sample_dtc_orders.jsonl --output-dir test_data/output/

# Check output
ls test_data/output/
# dtc_order_ledger_summary.csv
# dtc_order_snapshot_latest.csv
# dtc_fills.csv
```

## DTC Message Types Supported

| Type | Message                     | Pydantic Model                   |
| ---- | --------------------------- | -------------------------------- |
| 301  | OrderUpdate                 | ✅ `OrderUpdate`                 |
| 304  | HistoricalOrderFillResponse | ✅ `HistoricalOrderFillResponse` |
| 306  | PositionUpdate              | ✅ `PositionUpdate`              |
| 401  | TradeAccountResponse        | ✅ `TradeAccountResponse`        |
| 600  | AccountBalanceUpdate        | ✅ `AccountBalanceUpdate`        |

Additional message types can be easily added to `dtc_schemas.py`.

## Dependencies

- Python 3.9+
- pydantic >= 2.0

Install:

```bash
pip install pydantic
```

(Already installed in APPSIERRA .venv)
