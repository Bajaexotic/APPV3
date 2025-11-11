"""
tests/test_schema_integrity_standalone.py

Standalone automated validation of DTC Pydantic schemas.
No external dependencies beyond pydantic and services.dtc_schemas.

This version excludes database model tests (in case sqlmodel isn't installed).

Run with: python -m unittest tests.test_schema_integrity_standalone -v
Or: python -m pytest -q tests/test_schema_integrity_standalone.py --disable-warnings
"""

import unittest

from services.dtc_schemas import (
    DTC_MESSAGE_REGISTRY,
    AccountBalanceUpdate,
    BuySellEnum,
    DTCMessage,
    HistoricalOrderFillResponse,
    OrderStatusEnum,
    OrderTypeEnum,
    OrderUpdate,
    OrderUpdateReasonEnum,
    PositionUpdate,
    PositionUpdateReasonEnum,
    TradeAccountResponse,
    parse_dtc_message,
)


class TestDTCMessageRegistry(unittest.TestCase):
    """Test the DTC message type registry"""

    def test_registry_contains_all_implemented_types(self):
        """Verify all implemented message types are in registry"""
        expected_types = {301, 304, 306, 401, 600}
        actual_types = set(DTC_MESSAGE_REGISTRY.keys())
        self.assertEqual(actual_types, expected_types)

    def test_registry_maps_to_correct_classes(self):
        """Verify registry maps types to correct model classes"""
        expected_mapping = {
            301: OrderUpdate,
            304: HistoricalOrderFillResponse,
            306: PositionUpdate,
            401: TradeAccountResponse,
            600: AccountBalanceUpdate,
        }
        for msg_type, expected_class in expected_mapping.items():
            self.assertEqual(DTC_MESSAGE_REGISTRY[msg_type], expected_class)

    def test_all_registry_classes_inherit_from_dtc_message(self):
        """Verify all registered classes are DTC message subclasses"""
        for msg_type, msg_class in DTC_MESSAGE_REGISTRY.items():
            self.assertTrue(
                issubclass(msg_class, DTCMessage),
                f"Type {msg_type} ({msg_class.__name__}) should inherit from DTCMessage",
            )


class TestEnumIntegrity(unittest.TestCase):
    """Test enum value ranges and consistency"""

    def test_buy_sell_enum_values(self):
        """BuySellEnum should have values 1 and 2"""
        self.assertEqual(BuySellEnum.BUY.value, 1)
        self.assertEqual(BuySellEnum.SELL.value, 2)
        self.assertEqual(len(BuySellEnum), 2)

    def test_order_type_enum_values(self):
        """OrderTypeEnum should have values 1-5"""
        expected_values = [1, 2, 3, 4, 5]
        actual_values = sorted([e.value for e in OrderTypeEnum])
        self.assertEqual(actual_values, expected_values)

    def test_order_status_enum_values(self):
        """OrderStatusEnum should have values 0-9"""
        expected_count = 10  # 0 through 9
        self.assertEqual(len(OrderStatusEnum), expected_count)
        # Check specific status values
        self.assertEqual(OrderStatusEnum.ORDER_STATUS_NEW.value, 1)
        self.assertEqual(OrderStatusEnum.ORDER_STATUS_FILLED.value, 7)
        self.assertEqual(OrderStatusEnum.ORDER_STATUS_REJECTED.value, 8)
        self.assertEqual(OrderStatusEnum.ORDER_STATUS_PARTIALLY_FILLED.value, 9)

    def test_order_update_reason_enum_values(self):
        """OrderUpdateReasonEnum should have values 0-9"""
        expected_count = 9
        self.assertEqual(len(OrderUpdateReasonEnum), expected_count)
        # Check specific reasons
        self.assertEqual(OrderUpdateReasonEnum.NEW_ORDER_ACCEPTED.value, 1)
        self.assertEqual(OrderUpdateReasonEnum.ORDER_FILLED.value, 3)
        self.assertEqual(OrderUpdateReasonEnum.ORDER_CANCELED.value, 5)

    def test_position_update_reason_enum_values(self):
        """PositionUpdateReasonEnum should have values 0-2"""
        expected_count = 3
        self.assertEqual(len(PositionUpdateReasonEnum), expected_count)
        self.assertEqual(PositionUpdateReasonEnum.UNSOLICITED.value, 0)
        self.assertEqual(PositionUpdateReasonEnum.CURRENT_POSITIONS_REQUEST_RESPONSE.value, 1)
        self.assertEqual(PositionUpdateReasonEnum.POSITIONS_REQUEST_RESPONSE.value, 2)


class TestOrderUpdateSchema(unittest.TestCase):
    """Test OrderUpdate (Type 301) schema validation"""

    def test_order_update_type_literal(self):
        """Type 301 messages should parse as OrderUpdate"""
        raw = {"Type": 301, "ServerOrderID": "TEST"}
        msg = parse_dtc_message(raw)
        self.assertIsInstance(msg, OrderUpdate)

    def test_filled_order_payload(self):
        """Test complete filled order payload"""
        payload = {
            "Type": 301,
            "ServerOrderID": "ORD-12345",
            "Symbol": "MESZ24",
            "TradeAccount": "120005",
            "BuySell": 1,
            "OrderType": 2,
            "OrderStatus": 7,
            "OrderQuantity": 2,
            "Price1": 5800.25,
            "FilledQuantity": 2,
            "AverageFillPrice": 5800.50,
            "LastFillPrice": 5800.50,
            "LatestTransactionDateTime": 1730822500.0,
        }
        order = OrderUpdate.model_validate(payload)

        self.assertEqual(order.ServerOrderID, "ORD-12345")
        self.assertEqual(order.Symbol, "MESZ24")
        self.assertEqual(order.BuySell, 1)
        self.assertEqual(order.OrderStatus, 7)
        self.assertEqual(order.get_side(), "Buy")
        self.assertEqual(order.get_status(), "Filled")
        self.assertTrue(order.is_terminal())

    def test_partial_fill_payload(self):
        """Test partially filled order"""
        payload = {
            "Type": 301,
            "ServerOrderID": "PART-001",
            "Symbol": "NQEZ24",
            "OrderStatus": 9,
            "OrderUpdateReason": 4,
            "OrderQuantity": 10,
            "FilledQuantity": 6,
            "RemainingQuantity": 4,
        }
        order = OrderUpdate.model_validate(payload)

        self.assertEqual(order.OrderStatus, 9)
        self.assertEqual(order.get_status(), "PartiallyFilled")
        self.assertFalse(order.is_terminal())
        self.assertTrue(order.is_fill_update())

    def test_rejected_order_payload(self):
        """Test rejected order"""
        payload = {
            "Type": 301,
            "ServerOrderID": "REJ-001",
            "OrderStatus": 8,
            "OrderUpdateReason": 7,
            "RejectText": "Insufficient funds",
        }
        order = OrderUpdate.model_validate(payload)

        self.assertEqual(order.OrderStatus, 8)
        self.assertEqual(order.get_status(), "Rejected")
        self.assertTrue(order.is_terminal())
        self.assertEqual(order.get_text(), "Insufficient funds")

    def test_price_field_coalescing(self):
        """Test that price coalescing works with all variants"""
        # Test Price1
        order1 = OrderUpdate.model_validate({"Type": 301, "Price1": 100.0})
        self.assertEqual(order1.get_price(), 100.0)

        # Test Price
        order2 = OrderUpdate.model_validate({"Type": 301, "Price": 100.0})
        self.assertEqual(order2.get_price(), 100.0)

        # Test priority: Price1 takes precedence
        order3 = OrderUpdate.model_validate({"Type": 301, "Price1": 100.0, "Price": 200.0})
        self.assertEqual(order3.get_price(), 100.0)

    def test_quantity_field_coalescing(self):
        """Test that quantity coalescing works with all variants"""
        # Test OrderQuantity
        order1 = OrderUpdate.model_validate({"Type": 301, "OrderQuantity": 5})
        self.assertEqual(order1.get_quantity(), 5)

        # Test Quantity
        order2 = OrderUpdate.model_validate({"Type": 301, "Quantity": 5})
        self.assertEqual(order2.get_quantity(), 5)

        # Test priority: OrderQuantity takes precedence
        order3 = OrderUpdate.model_validate({"Type": 301, "OrderQuantity": 5, "Quantity": 10})
        self.assertEqual(order3.get_quantity(), 5)

    def test_text_field_coalescing(self):
        """Test that text field coalescing handles multiple variants"""
        # All text variants should be accessible
        payload = {
            "Type": 301,
            "InfoText": "Info",
            "TextMessage": "Message",
            "FreeFormText": "Freeform",
            "RejectText": "Rejection",
        }
        order = OrderUpdate.model_validate(payload)

        # Priority should be: InfoText > TextMessage > FreeFormText > RejectText
        self.assertEqual(order.get_text(), "Info")

    def test_timestamp_field_coalescing(self):
        """Test timestamp coalescing"""
        order1 = OrderUpdate.model_validate({"Type": 301, "LatestTransactionDateTime": 1730822500.0})
        self.assertEqual(order1.get_timestamp(), 1730822500.0)

        order2 = OrderUpdate.model_validate({"Type": 301, "OrderReceivedDateTime": 1730822400.0})
        self.assertEqual(order2.get_timestamp(), 1730822400.0)

        # LatestTransactionDateTime takes priority
        order3 = OrderUpdate.model_validate(
            {"Type": 301, "LatestTransactionDateTime": 1730822500.0, "OrderReceivedDateTime": 1730822400.0}
        )
        self.assertEqual(order3.get_timestamp(), 1730822500.0)

    def test_invalid_buy_sell_validation(self):
        """Test that invalid BuySell values are handled"""
        payload = {"Type": 301, "BuySell": 999}
        order = OrderUpdate.model_validate(payload)
        # Should parse without error but value may be None
        side = order.get_side()
        self.assertIsNone(side)

    def test_order_update_allows_extra_fields(self):
        """Test that OrderUpdate allows extra fields (for flexibility)"""
        payload = {
            "Type": 301,
            "ServerOrderID": "TEST",
            "UnknownField": "SomeValue",  # Extra field
            "AnotherUnknown": 123,
        }
        # Should not raise validation error due to Config.extra = "allow"
        order = OrderUpdate.model_validate(payload)
        self.assertEqual(order.ServerOrderID, "TEST")


class TestPositionUpdateSchema(unittest.TestCase):
    """Test PositionUpdate (Type 306) schema validation"""

    def test_position_update_type_literal(self):
        """Type 306 messages should parse as PositionUpdate"""
        raw = {"Type": 306, "Symbol": "MESZ24"}
        msg = parse_dtc_message(raw)
        self.assertIsInstance(msg, PositionUpdate)

    def test_long_position_payload(self):
        """Test long position"""
        payload = {
            "Type": 306,
            "Symbol": "MESZ24",
            "TradeAccount": "120005",
            "Quantity": 2,
            "AveragePrice": 5800.50,
            "OpenProfitLoss": 125.0,
        }
        pos = PositionUpdate.model_validate(payload)

        self.assertEqual(pos.Symbol, "MESZ24")
        self.assertEqual(pos.Quantity, 2)
        self.assertGreater(pos.Quantity, 0)  # Long

    def test_short_position_payload(self):
        """Test short position"""
        payload = {
            "Type": 306,
            "Symbol": "NQEZ24",
            "Quantity": -1,
            "AveragePrice": 20100.25,
        }
        pos = PositionUpdate.model_validate(payload)

        self.assertEqual(pos.Quantity, -1)
        self.assertLess(pos.Quantity, 0)  # Short

    def test_flat_position_payload(self):
        """Test flat (zero) position"""
        payload = {
            "Type": 306,
            "Symbol": "MESZ24",
            "Quantity": 0,
            "NoPositions": 1,
        }
        pos = PositionUpdate.model_validate(payload)

        self.assertEqual(pos.Quantity, 0)
        self.assertEqual(pos.NoPositions, 1)


class TestHistoricalOrderFillSchema(unittest.TestCase):
    """Test HistoricalOrderFillResponse (Type 304) schema"""

    def test_historical_fill_payload(self):
        """Test historical order fill response"""
        payload = {
            "Type": 304,
            "ServerOrderID": "ORD-HIST-001",
            "Symbol": "MESZ24",
            "TradeAccount": "120005",
            "BuySell": 1,
            "Quantity": 2,
            "Price": 5800.50,
            "DateTime": 1730822500.0,
            "Commission": 12.50,
        }
        fill = HistoricalOrderFillResponse.model_validate(payload)

        self.assertEqual(fill.ServerOrderID, "ORD-HIST-001")
        self.assertEqual(fill.Symbol, "MESZ24")
        self.assertEqual(fill.BuySell, 1)
        self.assertEqual(fill.get_side(), "Buy")
        self.assertEqual(fill.Commission, 12.50)


class TestAccountBalanceSchema(unittest.TestCase):
    """Test AccountBalanceUpdate (Type 600) schema"""

    def test_account_balance_payload(self):
        """Test account balance update"""
        payload = {
            "Type": 600,
            "TradeAccount": "120005",
            "CashBalance": 50000.0,
            "BalanceAvailableForNewPositions": 48000.0,
            "AccountValue": 100000.0,
            "AvailableFunds": 48000.0,
            "MarginRequirement": 2000.0,
            "SecuritiesValue": 50000.0,
            "OpenPositionsProfitLoss": 250.0,
            "DailyProfitLoss": 100.0,
        }
        balance = AccountBalanceUpdate.model_validate(payload)

        self.assertEqual(balance.TradeAccount, "120005")
        self.assertEqual(balance.CashBalance, 50000.0)
        self.assertEqual(balance.AccountValue, 100000.0)
        self.assertEqual(balance.OpenPositionsProfitLoss, 250.0)


class TestTradeAccountSchema(unittest.TestCase):
    """Test TradeAccountResponse (Type 401) schema"""

    def test_trade_account_response_payload(self):
        """Test trade account response"""
        payload = {
            "Type": 401,
            "TradeAccount": "120005",
            "AccountName": "Main Trading Account",
            "RequestID": 1,
        }
        account = TradeAccountResponse.model_validate(payload)

        self.assertEqual(account.TradeAccount, "120005")
        self.assertEqual(account.AccountName, "Main Trading Account")


class TestParsingRobustness(unittest.TestCase):
    """Test parsing robustness with edge cases"""

    def test_parse_with_missing_optional_fields(self):
        """Test parsing with only required fields"""
        payload = {"Type": 301, "ServerOrderID": "MIN-001"}
        order = parse_dtc_message(payload)

        self.assertIsInstance(order, OrderUpdate)
        self.assertEqual(order.ServerOrderID, "MIN-001")
        self.assertIsNone(order.Symbol)
        self.assertIsNone(order.BuySell)

    def test_parse_unknown_type_fallback(self):
        """Test that unknown message types fall back to DTCMessage"""
        payload = {"Type": 9999, "CustomField": "value"}
        msg = parse_dtc_message(payload)

        # Should parse as generic DTCMessage, not throw error
        self.assertIsInstance(msg, DTCMessage)
        self.assertEqual(msg.Type, 9999)

    def test_parse_with_extra_fields(self):
        """Test parsing with fields not in schema"""
        payload = {
            "Type": 301,
            "ServerOrderID": "TEST",
            "CustomField1": "value",
            "CustomField2": 123,
            "CustomField3": 45.67,
        }
        order = parse_dtc_message(payload)

        # Should parse without error due to extra = "allow"
        self.assertIsInstance(order, OrderUpdate)
        self.assertEqual(order.ServerOrderID, "TEST")


class TestSchemaConsistency(unittest.TestCase):
    """Test consistency across schemas"""

    def test_all_schemas_have_optional_type_field(self):
        """Verify all schemas allow optional Type field"""
        schemas = [
            OrderUpdate,
            HistoricalOrderFillResponse,
            PositionUpdate,
            TradeAccountResponse,
            AccountBalanceUpdate,
        ]

        for schema_class in schemas:
            # Each should have Type field defined
            self.assertIn("Type", schema_class.model_fields)

    def test_all_schemas_inherit_from_dtc_message(self):
        """Verify all concrete schemas inherit from DTCMessage"""
        schemas = [
            OrderUpdate,
            HistoricalOrderFillResponse,
            PositionUpdate,
            TradeAccountResponse,
            AccountBalanceUpdate,
        ]

        for schema_class in schemas:
            self.assertTrue(
                issubclass(schema_class, DTCMessage), f"{schema_class.__name__} should inherit from DTCMessage"
            )

    def test_enum_values_are_integers(self):
        """Verify all enums use integer values"""
        enums = [
            BuySellEnum,
            OrderTypeEnum,
            OrderStatusEnum,
            OrderUpdateReasonEnum,
            PositionUpdateReasonEnum,
        ]

        for enum_class in enums:
            for member in enum_class:
                self.assertIsInstance(member.value, int, f"{enum_class.__name__}.{member.name} should have int value")


# Integration-style tests
class TestRealWorldScenarios(unittest.TestCase):
    """Test real-world trading scenarios"""

    def test_full_order_lifecycle(self):
        """Test a complete order lifecycle: submit → fill → cancel"""

        # Order submitted
        submit_payload = {
            "Type": 301,
            "ServerOrderID": "ORD-LIFECYCLE-001",
            "Symbol": "MESZ24",
            "BuySell": 1,
            "OrderType": 2,
            "OrderStatus": 2,  # SUBMITTED
            "OrderUpdateReason": 1,  # NEW_ORDER_ACCEPTED
            "OrderQuantity": 5,
            "Price1": 5800.0,
        }
        order = parse_dtc_message(submit_payload)
        self.assertEqual(order.get_status(), "Submitted")
        self.assertFalse(order.is_terminal())

        # Partial fill
        fill_payload = {
            "Type": 301,
            "ServerOrderID": "ORD-LIFECYCLE-001",
            "OrderStatus": 9,  # PARTIALLY_FILLED
            "OrderUpdateReason": 4,  # ORDER_FILLED_PARTIALLY
            "FilledQuantity": 3,
            "RemainingQuantity": 2,
            "AverageFillPrice": 5800.25,
        }
        order = parse_dtc_message(fill_payload)
        self.assertEqual(order.get_status(), "PartiallyFilled")
        self.assertTrue(order.is_fill_update())
        self.assertFalse(order.is_terminal())

        # Complete fill
        final_payload = {
            "Type": 301,
            "ServerOrderID": "ORD-LIFECYCLE-001",
            "OrderStatus": 7,  # FILLED
            "OrderUpdateReason": 3,  # ORDER_FILLED
            "FilledQuantity": 5,
            "RemainingQuantity": 0,
            "AverageFillPrice": 5800.30,
            "LatestTransactionDateTime": 1730822600.0,
        }
        order = parse_dtc_message(final_payload)
        self.assertEqual(order.get_status(), "Filled")
        self.assertTrue(order.is_terminal())
        self.assertTrue(order.is_fill_update())

    def test_balance_update_sequence(self):
        """Test sequence of balance updates"""
        initial = AccountBalanceUpdate.model_validate(
            {
                "Type": 600,
                "TradeAccount": "120005",
                "CashBalance": 100000.0,
                "AccountValue": 100000.0,
            }
        )
        self.assertEqual(initial.CashBalance, 100000.0)

        # After trade
        after_trade = AccountBalanceUpdate.model_validate(
            {
                "Type": 600,
                "TradeAccount": "120005",
                "CashBalance": 99750.0,
                "AccountValue": 100250.0,
                "OpenPositionsProfitLoss": 250.0,
            }
        )
        self.assertEqual(after_trade.CashBalance, 99750.0)
        self.assertEqual(after_trade.OpenPositionsProfitLoss, 250.0)


if __name__ == "__main__":
    # Run with verbose output
    unittest.main(verbosity=2)
