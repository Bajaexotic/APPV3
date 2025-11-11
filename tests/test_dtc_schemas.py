"""
tests/test_dtc_schemas.py

Unit tests for DTC Pydantic schema validation and parsing.
Verifies OrderUpdate and PositionUpdate models work correctly with real DTC messages.
"""

import unittest

from services.dtc_schemas import (
    BuySellEnum,
    OrderStatusEnum,
    OrderTypeEnum,
    OrderUpdate,
    PositionUpdate,
    parse_dtc_message,
)


class TestOrderUpdateParsing(unittest.TestCase):
    """Test OrderUpdate Pydantic model parsing"""

    def test_parse_filled_order(self):
        """Test parsing a filled order (Type 301, Status 7)"""
        raw = {
            "Type": 301,
            "ServerOrderID": "ORD-12345",
            "Symbol": "MESZ24",
            "TradeAccount": "120005",
            "BuySell": 1,  # Buy
            "OrderType": 2,  # Limit
            "OrderStatus": 7,  # Filled
            "OrderQuantity": 2,
            "Price1": 5800.25,
            "FilledQuantity": 2,
            "AverageFillPrice": 5800.50,
            "LastFillPrice": 5800.50,
            "LatestTransactionDateTime": 1730822500.0,
        }

        order = parse_dtc_message(raw)

        self.assertIsInstance(order, OrderUpdate)
        self.assertEqual(order.ServerOrderID, "ORD-12345")
        self.assertEqual(order.Symbol, "MESZ24")
        self.assertEqual(order.BuySell, 1)
        self.assertEqual(order.OrderStatus, 7)
        self.assertTrue(order.is_terminal())
        self.assertTrue(order.is_fill_update())
        self.assertEqual(order.get_side(), "Buy")
        self.assertEqual(order.get_status(), "Filled")
        self.assertEqual(order.get_order_type(), "Limit")

    def test_parse_canceled_order(self):
        """Test parsing a canceled order (Type 301, Status 6)"""
        raw = {
            "Type": 301,
            "ServerOrderID": "ORD-67890",
            "Symbol": "NQEZ24",
            "BuySell": 2,  # Sell
            "OrderType": 1,  # Market
            "OrderStatus": 6,  # Canceled
            "OrderQuantity": 1,
            "InfoText": "User canceled",
        }

        order = parse_dtc_message(raw)

        self.assertIsInstance(order, OrderUpdate)
        self.assertEqual(order.get_side(), "Sell")
        self.assertEqual(order.get_status(), "Canceled")
        self.assertTrue(order.is_terminal())
        self.assertFalse(order.is_fill_update())
        self.assertEqual(order.get_text(), "User canceled")

    def test_field_coalescing(self):
        """Test Pydantic field coalescing helpers"""
        raw = {
            "Type": 301,
            "ServerOrderID": "TEST-001",
            # Test price coalescing
            "Price1": 5800.0,
            # Test quantity coalescing
            "OrderQuantity": 3,
            # Test avg fill coalescing
            "AverageFillPrice": 5801.25,
            # Test timestamp coalescing
            "LatestTransactionDateTime": 1730822600.0,
        }

        order = parse_dtc_message(raw)

        self.assertEqual(order.get_price(), 5800.0)
        self.assertEqual(order.get_quantity(), 3)
        self.assertEqual(order.get_avg_fill_price(), 5801.25)
        self.assertEqual(order.get_timestamp(), 1730822600.0)

    def test_high_low_during_position(self):
        """Test HighDuringPosition and LowDuringPosition extraction"""
        raw = {
            "Type": 301,
            "ServerOrderID": "TEST-002",
            "HighDuringPosition": 5850.0,
            "LowDuringPosition": 5780.0,
        }

        order = parse_dtc_message(raw)

        self.assertEqual(order.get_high_during_position(), 5850.0)
        self.assertEqual(order.get_low_during_position(), 5780.0)

    def test_partial_fill(self):
        """Test partially filled order detection"""
        raw = {
            "Type": 301,
            "ServerOrderID": "TEST-003",
            "OrderStatus": 9,  # PartiallyFilled
            "OrderUpdateReason": 4,  # PartialFill
            "OrderQuantity": 5,
            "FilledQuantity": 3,
        }

        order = parse_dtc_message(raw)

        self.assertEqual(order.get_status(), "PartiallyFilled")
        self.assertFalse(order.is_terminal())  # Not fully terminal yet
        self.assertTrue(order.is_fill_update())  # But is a fill event


class TestPositionUpdateParsing(unittest.TestCase):
    """Test PositionUpdate Pydantic model parsing"""

    def test_parse_long_position(self):
        """Test parsing a long position (Type 306)"""
        raw = {
            "Type": 306,
            "Symbol": "MESZ24",
            "TradeAccount": "120005",
            "Quantity": 2,  # Positive = long
            "AveragePrice": 5800.50,
            "OpenProfitLoss": 125.0,
            "UpdateReason": "Unsolicited",
        }

        pos = parse_dtc_message(raw)

        self.assertIsInstance(pos, PositionUpdate)
        self.assertEqual(pos.Symbol, "MESZ24")
        self.assertEqual(pos.Quantity, 2)
        self.assertEqual(pos.AveragePrice, 5800.50)
        self.assertEqual(pos.OpenProfitLoss, 125.0)

    def test_parse_short_position(self):
        """Test parsing a short position (Type 306)"""
        raw = {
            "Type": 306,
            "Symbol": "NQEZ24",
            "Quantity": -1,  # Negative = short
            "AveragePrice": 20100.25,
        }

        pos = parse_dtc_message(raw)

        self.assertEqual(pos.Quantity, -1)
        self.assertEqual(pos.AveragePrice, 20100.25)

    def test_parse_flat_position(self):
        """Test parsing a flat (zero) position"""
        raw = {
            "Type": 306,
            "Symbol": "MESZ24",
            "Quantity": 0,  # Flat
            "NoPositions": 1,
        }

        pos = parse_dtc_message(raw)

        self.assertEqual(pos.Quantity, 0)
        self.assertEqual(pos.NoPositions, 1)


class TestPydanticValidation(unittest.TestCase):
    """Test Pydantic validation catches malformed messages"""

    def test_invalid_buy_sell(self):
        """Invalid BuySell value should be handled gracefully"""
        raw = {
            "Type": 301,
            "ServerOrderID": "TEST-004",
            "BuySell": 999,  # Invalid
        }

        order = parse_dtc_message(raw)

        # Should parse but BuySell might be set to None
        self.assertIsInstance(order, OrderUpdate)
        # get_side() should handle None gracefully
        side = order.get_side()
        self.assertIsNone(side)

    def test_missing_optional_fields(self):
        """Missing optional fields should not break parsing"""
        raw = {
            "Type": 301,
            "ServerOrderID": "TEST-005",
            # All other fields missing
        }

        order = parse_dtc_message(raw)

        self.assertIsInstance(order, OrderUpdate)
        self.assertEqual(order.ServerOrderID, "TEST-005")
        # Optional fields should be None
        self.assertIsNone(order.Symbol)
        self.assertIsNone(order.BuySell)

    def test_unknown_message_type(self):
        """Unknown message type should fall back to generic DTCMessage"""
        raw = {
            "Type": 9999,  # Unknown
            "SomeField": "value",
        }

        msg = parse_dtc_message(raw)

        # Should still parse, just not as specialized model
        self.assertEqual(msg.Type, 9999)


if __name__ == "__main__":
    unittest.main(verbosity=2)
