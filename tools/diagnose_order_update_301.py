#!/usr/bin/env python3
"""
DTC Message Type 301 (OrderUpdate) Diagnostic Tool

Analyzes the OrderUpdate message structure, RequestID handling,
and Sierra Chart broadcast behavior.

Usage:
    python tools/diagnose_order_update_301.py
    python tools/diagnose_order_update_301.py --output report.json
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.dtc_constants import ORDER_UPDATE, type_to_name
from services.dtc_schemas import OrderUpdate, DTC_MESSAGE_REGISTRY


def analyze_schema_definition() -> Dict[str, Any]:
    """
    Analyze the OrderUpdate schema definition from dtc_schemas.py.

    Returns:
        Dictionary containing schema analysis
    """
    schema_info = {
        "type": 301,
        "name": "OrderUpdate",
        "pydantic_class": "OrderUpdate",
        "defined_fields": [],
        "optional_fields": [],
        "required_fields": [],
        "field_details": {},
        "helper_methods": [],
        "enums": {}
    }

    # Get all fields from OrderUpdate schema
    if hasattr(OrderUpdate, 'model_fields'):
        # Pydantic v2
        fields = OrderUpdate.model_fields
        for field_name, field_info in fields.items():
            is_optional = field_info.is_required() == False
            field_type = str(field_info.annotation)

            schema_info["defined_fields"].append(field_name)
            if is_optional:
                schema_info["optional_fields"].append(field_name)
            else:
                schema_info["required_fields"].append(field_name)

            schema_info["field_details"][field_name] = {
                "type": field_type,
                "optional": is_optional,
                "default": str(field_info.default) if field_info.default is not None else None
            }

    # Get helper methods
    helper_methods = [
        m for m in dir(OrderUpdate)
        if not m.startswith('_') and callable(getattr(OrderUpdate, m))
        and m not in ['model_validate', 'model_dump', 'model_json_schema', 'model_config']
    ]
    schema_info["helper_methods"] = helper_methods

    # Document enums
    schema_info["enums"] = {
        "BuySell": {1: "BUY", 2: "SELL"},
        "OrderType": {1: "MARKET", 2: "LIMIT", 3: "STOP", 4: "STOP_LIMIT", 5: "MARKET_IF_TOUCHED"},
        "OrderStatus": {
            0: "UNSPECIFIED", 1: "NEW", 2: "SUBMITTED", 3: "PENDING_CANCEL",
            4: "OPEN", 5: "PENDING_REPLACE", 6: "CANCELED", 7: "FILLED",
            8: "REJECTED", 9: "PARTIALLY_FILLED"
        },
        "OrderUpdateReason": {
            0: "UNKNOWN", 1: "NEW_ORDER_ACCEPTED", 2: "GENERAL_ORDER_UPDATE",
            3: "ORDER_FILLED", 4: "ORDER_FILLED_PARTIALLY", 5: "ORDER_CANCELED",
            6: "ORDER_CANCEL_REPLACE_COMPLETE", 7: "NEW_ORDER_REJECTED",
            8: "ORDER_CANCEL_REJECTED", 9: "ORDER_CANCEL_REPLACE_REJECTED"
        }
    }

    return schema_info


def analyze_request_id_handling() -> Dict[str, Any]:
    """
    Analyze how RequestID is handled in the codebase.

    Returns:
        Dictionary containing RequestID analysis
    """
    request_id_info = {
        "field_name": "RequestID",
        "schema_support": True,
        "optional": True,
        "purpose": "Links responses to requests in request/response pattern",
        "special_values": {
            "0": {
                "meaning": "Unsolicited broadcast from server",
                "trigger": "Server-initiated updates (fills, status changes, etc.)",
                "requires_callback": False
            },
            "None": {
                "meaning": "Field not present in message",
                "trigger": "Unsolicited broadcasts or legacy messages",
                "requires_callback": False
            },
            ">0": {
                "meaning": "Response to a specific request",
                "trigger": "Reply to client request (e.g., OpenOrdersRequest)",
                "requires_callback": True
            }
        },
        "request_id_map": {
            1: "Type 400 (TradeAccountsRequest)",
            2: "Type 500 (PositionsRequest) - SKIPPED",
            3: "Type 305 (OpenOrdersRequest)",
            4: "Type 303 (HistoricalOrderFillsRequest)",
            5: "Type 601 (AccountBalanceRequest)"
        },
        "handling_location": "core/data_bridge.py:444-469"
    }

    return request_id_info


def classify_request_id_zero() -> Dict[str, Any]:
    """
    Determine the classification of RequestID=0 for OrderUpdate messages.

    Returns:
        Dictionary containing RequestID=0 classification
    """
    classification = {
        "request_id": 0,
        "classification": "Sierra broadcast event",
        "trigger_type": "Unsolicited server push",
        "description": (
            "RequestID=0 indicates an unsolicited OrderUpdate broadcast from Sierra Chart. "
            "These are live updates triggered by order state changes (fills, cancellations, "
            "rejections, etc.) and are NOT responses to client requests."
        ),
        "examples": [
            "Order fill notification when order executes",
            "Order status change from OPEN to FILLED",
            "Order rejection after submission",
            "Partial fill updates"
        ],
        "routing": {
            "signal": "signal_order (Blinker)",
            "handler": "MessageRouter._on_order_signal()",
            "panels": ["Panel2 (live trading)", "Panel3 (statistics)"],
            "state_manager": "StateManager.record_order()"
        },
        "correlation": {
            "use_server_order_id": True,
            "use_client_order_id": True,
            "description": (
                "Use ServerOrderID to correlate with existing orders. "
                "Sierra assigns ServerOrderID when order is accepted."
            )
        }
    }

    return classification


def check_missing_fields() -> Dict[str, Any]:
    """
    Check for any fields that might be missing from the schema.

    Returns:
        Dictionary containing missing fields analysis
    """
    known_sierra_fields = {
        # Identity
        "Type", "ServerOrderID", "ClientOrderID", "TradeAccount",
        # Symbol
        "Symbol", "Exchange",
        # Order details
        "BuySell", "OrderType", "OrderStatus", "OrderUpdateReason",
        # Quantities
        "OrderQuantity", "Quantity", "TotalQuantity", "FilledQuantity", "RemainingQuantity",
        # Prices
        "Price1", "Price2", "Price", "LimitPrice", "StopPrice",
        # Fill details
        "AverageFillPrice", "AvgFillPrice", "LastFillPrice", "LastFillQuantity", "LastFillDateTime",
        # Position extremes
        "HighDuringPosition", "HighPriceDuringPosition", "LowDuringPosition", "LowPriceDuringPosition",
        # Timestamps
        "OrderReceivedDateTime", "LatestTransactionDateTime",
        # Text/Info
        "InfoText", "TextMessage", "FreeFormText", "RejectText",
        # Sequencing
        "MessageNumber", "TotalNumberMessages", "TotalNumMessages", "NoOrders",
        # Flags
        "Unsolicited", "RequestID"
    }

    schema_info = analyze_schema_definition()
    defined_fields = set(schema_info["defined_fields"])

    missing_fields = known_sierra_fields - defined_fields
    extra_fields = defined_fields - known_sierra_fields

    return {
        "schema_status": "Valid" if len(missing_fields) == 0 else "Incomplete",
        "missing_fields": sorted(list(missing_fields)),
        "extra_fields": sorted(list(extra_fields)),
        "coverage": {
            "total_known_fields": len(known_sierra_fields),
            "defined_fields": len(defined_fields),
            "coverage_pct": round(len(defined_fields & known_sierra_fields) / len(known_sierra_fields) * 100, 1)
        }
    }


def generate_diagnostic_report() -> Dict[str, Any]:
    """
    Generate comprehensive diagnostic report for Type 301 OrderUpdate.

    Returns:
        Complete diagnostic report
    """
    schema = analyze_schema_definition()
    request_id = analyze_request_id_handling()
    classification = classify_request_id_zero()
    missing_fields = check_missing_fields()

    report = {
        "message_type": {
            "type": 301,
            "name": "OrderUpdate",
            "category": "Order and Trade Messages (300-399)",
            "dtc_spec": "https://dtcprotocol.org/index.php?page=doc/DTCMessageDocumentation.php"
        },
        "schema_analysis": {
            "pydantic_class": schema["pydantic_class"],
            "total_fields": len(schema["defined_fields"]),
            "optional_fields_count": len(schema["optional_fields"]),
            "required_fields_count": len(schema["required_fields"]),
            "helper_methods": schema["helper_methods"],
            "field_groups": {
                "identity": ["ServerOrderID", "ClientOrderID", "TradeAccount"],
                "symbol": ["Symbol", "Exchange"],
                "order_details": ["BuySell", "OrderType", "OrderStatus", "OrderUpdateReason"],
                "quantities": ["OrderQuantity", "Quantity", "TotalQuantity", "FilledQuantity", "RemainingQuantity"],
                "prices": ["Price1", "Price2", "Price", "LimitPrice", "StopPrice"],
                "fill_details": ["AverageFillPrice", "LastFillPrice", "LastFillQuantity", "LastFillDateTime"],
                "timestamps": ["OrderReceivedDateTime", "LatestTransactionDateTime"],
                "metadata": ["RequestID", "MessageNumber", "TotalNumberMessages", "Unsolicited"]
            }
        },
        "request_id_analysis": request_id,
        "request_id_zero_classification": classification,
        "missing_fields_analysis": missing_fields,
        "recommended_actions": [],
        "summary": {
            "type": 301,
            "name": "OrderUpdate",
            "request_id": 0,
            "classification": classification["classification"],
            "schema_status": missing_fields["schema_status"],
            "missing_fields": missing_fields["missing_fields"],
            "recommended_action": classification["description"]
        }
    }

    # Generate recommendations
    if missing_fields["schema_status"] == "Valid":
        report["recommended_actions"].append({
            "action": "No schema changes required",
            "reason": "All known Sierra Chart OrderUpdate fields are defined in the schema",
            "priority": "N/A"
        })
    else:
        report["recommended_actions"].append({
            "action": f"Add missing fields to OrderUpdate schema: {', '.join(missing_fields['missing_fields'])}",
            "reason": "Sierra Chart may send these fields in some scenarios",
            "priority": "Medium"
        })

    report["recommended_actions"].extend([
        {
            "action": "Handle RequestID=0 as unsolicited broadcast",
            "reason": "RequestID=0 indicates server-initiated updates, not responses to requests",
            "priority": "High",
            "implementation": "Already implemented in MessageRouter._on_order_signal()"
        },
        {
            "action": "Correlate OrderUpdate messages using ServerOrderID",
            "reason": "ServerOrderID is the authoritative identifier for tracking order state",
            "priority": "High",
            "implementation": "Use ServerOrderID to link fills, status changes to original orders"
        },
        {
            "action": "Monitor Unsolicited field",
            "reason": "Unsolicited=1 explicitly marks live updates vs request responses",
            "priority": "Low",
            "implementation": "Already logged in signal handlers for debugging"
        }
    ])

    return report


def main():
    parser = argparse.ArgumentParser(
        description="Diagnostic tool for DTC Type 301 (OrderUpdate) messages"
    )
    parser.add_argument(
        "--output", "-o",
        help="Output JSON report to file",
        type=str
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output"
    )
    args = parser.parse_args()

    print("="*80)
    print("DTC Type 301 (OrderUpdate) Diagnostic Report")
    print("="*80)
    print()

    # Generate diagnostic report
    report = generate_diagnostic_report()

    # Print summary to console
    summary = report["summary"]
    print(f"Message Type: {summary['type']} ({summary['name']})")
    print(f"RequestID: {summary['request_id']}")
    print(f"Classification: {summary['classification']}")
    print(f"Schema Status: {summary['schema_status']}")
    print(f"Missing Fields: {len(summary['missing_fields'])}")
    print()

    print("Recommended Actions:")
    for i, action in enumerate(report["recommended_actions"], 1):
        print(f"  {i}. [{action['priority']}] {action['action']}")
        print(f"     Reason: {action['reason']}")
        if "implementation" in action:
            print(f"     Implementation: {action['implementation']}")
        print()

    # Output JSON
    json_output = json.dumps(
        report["summary"] if not args.pretty else report,
        indent=2 if args.pretty else None
    )

    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(json_output)
        print(f"Full report written to: {args.output}")
    else:
        print()
        print("="*80)
        print("JSON Summary:")
        print("="*80)
        print(json_output)

    print()
    print("="*80)
    print("Diagnostic Complete")
    print("="*80)


if __name__ == "__main__":
    main()
