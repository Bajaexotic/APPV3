from __future__ import annotations


"""
services/__init__.py

Package export surface for services layer.
Exposes commonly-used classes and functions for import convenience.
"""

# Core business logic exports
from .dtc_schemas import OrderUpdate, PositionUpdate, parse_dtc_message
from .live_state import load_open_position
from .stats_service import compute_trading_stats_for_timeframe
from .trade_constants import COMM_PER_CONTRACT, DOLLARS_PER_POINT
from .trade_math import TradeMath
from .trade_store import record_closed_trade

# Note: Mock modules (ep_price_feed, ep_reader, json_parser) are available
# for direct import but not exported here. Use for testing only.
